"""Host-owned budgets and RPC boundary for untrusted workflow candidates."""
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import tarfile
import tempfile
import time
from gemma_lab.sandbox import DockerSandbox
from gemma_lab.tools import TOOLS, validate

RUNTIME_FILES = ('src/gemma_lab/__init__.py', 'src/gemma_lab/agent.py', 'src/gemma_lab/tools.py',
                 'docker/local/tools.py', 'tests/test_agent.py')

class BudgetExceeded(Exception):
    pass


def copy_runtime(container, root, overrides):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as archive:
        for name in RUNTIME_FILES:
            text = overrides.get(name, (root / name).read_text()).encode()
            entry = tarfile.TarInfo(name)
            entry.mode, entry.size = 0o444, len(text)
            archive.addfile(entry, io.BytesIO(text))
    result = container._exec(['tar', '-xf', '-', '--no-same-owner', '-C', '/workspace'], data.getvalue(), timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    container.copy_file(root / 'docker/workflow_runtime/runner.py', '/tmp')


def validate_runtime(root, settings, overrides):
    with DockerSandbox(settings['image'], timeout=30, output_limit=12000) as runtime:
        copy_runtime(runtime, root, overrides)
        return runtime.run_command('python -m unittest discover -s tests -p test_agent.py -v')

def limited_exec(container, arguments, data=b'', timeout=30, limit=32000):
    if len(data) > 256000:
        raise BudgetExceeded('tool_input_limit')
    with tempfile.TemporaryFile() as input_file:
        input_file.write(data)
        input_file.seek(0)
        process = subprocess.Popen(['docker', 'exec', '-i', '-w', '/workspace', container.name, *arguments],
                                   stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
        buffers = {'stdout': bytearray(), 'stderr': bytearray()}
        deadline = time.monotonic() + timeout
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BudgetExceeded('tool_timeout')
                for key, _ in selector.select(min(1, remaining)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(chunk)
                    if sum(len(value) for value in buffers.values()) > limit:
                        raise BudgetExceeded('tool_output_limit')
            code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
            return subprocess.CompletedProcess(arguments, code, bytes(buffers['stdout']), bytes(buffers['stderr']))
        finally:
            selector.close()
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
            process.stderr.close()


class Authority:
    def __init__(self, client, task, settings, run, system, issue):
        self.client, self.task, self.settings, self.run = client, task, settings, run
        self.system, self.issue = system, issue
        self.deadline = time.monotonic() + settings['time_limit_seconds']
        self.turns = self.calls = self.snapshots = 0
        self.usage = {'prompt_tokens': 0, 'completion_tokens': 0}
        self.last_patch = None
        self.finished = None
        self.base_head = task._exec(['git', 'rev-parse', 'HEAD']).stdout.decode().strip()

    def event(self, kind, **data):
        with (self.run / 'trajectory.jsonl').open('a') as output:
            output.write(json.dumps({'time': time.time(), 'event': kind, **data}) + '\n')
        if kind in ('tool_call', 'finished', 'rejected'):
            print(json.dumps({'event': kind, **data})[:700], flush=True)

    def dispatch(self, request):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise BudgetExceeded('time_limit')
        operation = request.get('operation')
        if operation == 'complete':
            if self.turns >= self.settings['max_turns']:
                raise BudgetExceeded('turn_limit')
            messages = request.get('messages')
            if not isinstance(messages, list) or not messages or messages[0] != {'role': 'system', 'content': self.system}:
                raise ValueError('The frozen system prompt must remain unchanged')
            if not any(m.get('role') == 'user' and m.get('content') == self.issue for m in messages):
                raise ValueError('Original issue must remain in context')
            if len(json.dumps(messages)) > 100000:
                raise ValueError('Context message payload is too large')
            self.turns += 1
            result = self.client.complete(messages, TOOLS, timeout=max(1, remaining))
            for key in self.usage:
                self.usage[key] += result.get('usage', {}).get(key, 0)
            self.event('response', response=result)
            return result
        if operation == 'tool':
            if self.calls >= self.settings['max_tool_calls']:
                raise BudgetExceeded('tool_limit')
            name, arguments = request.get('name'), request.get('arguments')
            validate(name, arguments)
            if name not in {'run_command', 'read_file', 'edit_file', 'write_file'}:
                raise ValueError('Only repository operations are dispatched through this endpoint')
            self.calls += 1
            self.event('tool_call', name=name, raw_arguments=json.dumps(arguments))
            # Candidate helper runs only inside the task container.
            payload = json.dumps({'name': name, 'arguments': arguments,
                'timeout': min(self.settings['command_timeout_seconds'], max(1, remaining)),
                'output_limit': self.settings['tool_output_chars']}).encode()
            result = limited_exec(self.task, ['python', '/tmp/candidate-tools.py'], payload,
                                  timeout=min(remaining, self.settings['command_timeout_seconds'] + 5))
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors='replace')[:2000])
            if len(result.stdout) > 32000:
                raise ValueError('Tool response exceeds host limit')
            result = json.loads(result.stdout)
            self.event('tool_result', name=name, result=result)
            return result
        if operation == 'snapshot':
            if self.calls >= self.settings['max_tool_calls']:
                raise BudgetExceeded('tool_limit')
            self.calls += 1
            self.snapshots += 1
            if self.snapshots > 8:
                raise BudgetExceeded('snapshot_limit')
            head = limited_exec(self.task, ['git', 'rev-parse', 'HEAD'], timeout=min(remaining, 10)).stdout.decode().strip()
            if head != self.base_head:
                raise ValueError('Task Git history was modified')
            result = limited_exec(self.task, ['bash', '-c', 'git add -N . && git --no-pager diff --no-ext-diff --no-textconv --binary ' + self.base_head],
                                  timeout=min(remaining, 20), limit=4 * 1024 * 1024)
            if result.returncode:
                raise ValueError(result.stderr.decode(errors='replace'))
            self.last_patch = result.stdout.decode()
            (self.run / 'candidate.diff').write_text(self.last_patch)
            return self.last_patch
        if operation == 'finish':
            claimed = request.get('outcome') or {}
            reason = claimed.get('reason', 'runtime_error')
            if reason == 'submitted' and not (self.last_patch or '').strip():
                reason = 'empty_patch'
            self.finished = {'reason': reason, 'turns': self.turns, 'tool_calls': self.calls,
                             'usage': dict(self.usage), 'candidate_claim': claimed}
            self.event('finished', **self.finished)
            return self.finished
        raise ValueError('Unknown runtime RPC operation')


def bridge(process, authority, stderr_path):
    """Read bounded binary frames with a host deadline, including silent/hung runtimes."""
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
    pending = b''
    total = stderr_count = 0
    with stderr_path.open('wb') as errors:
        try:
            while authority.finished is None:
                remaining = authority.deadline - time.monotonic()
                if remaining <= 0:
                    raise BudgetExceeded('time_limit')
                events = selector.select(min(remaining, 1))
                if not events and process.poll() is not None:
                    raise RuntimeError('Runtime exited without a result')
                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'stderr':
                        errors.write(chunk[:max(0, 65536 - stderr_count)])
                        stderr_count += len(chunk)
                        continue
                    total += len(chunk)
                    pending += chunk
                    if total > 8 * 1024 * 1024 or len(pending) > 1024 * 1024:
                        raise ValueError('Runtime output budget exceeded')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        request = json.loads(line)
                        try:
                            response = authority.dispatch(request)
                            reply = {'ok': True, 'result': response}
                        except BudgetExceeded:
                            raise
                        except TimeoutError:
                            if time.monotonic() >= authority.deadline:
                                raise BudgetExceeded('time_limit')
                            raise
                        except Exception as error:
                            authority.event('rejected', error=str(error))
                            reply = {'ok': False, 'error': str(error)}
                        process.stdin.write((json.dumps(reply) + '\n').encode())
                        process.stdin.flush()
                        if authority.finished is not None:
                            return authority.finished
        except BudgetExceeded as error:
            return {'reason': str(error), 'turns': authority.turns, 'tool_calls': authority.calls,
                    'usage': authority.usage}
        finally:
            selector.close()


def run_runtime(root, source, commit, settings, client, issue, system, run, overrides):
    with DockerSandbox(settings['image'], settings['command_timeout_seconds'], settings['tool_output_chars']) as task, \
         DockerSandbox(settings['image'], timeout=30, output_limit=12000) as runtime:
        task.checkout(source, commit)
        helper = run / 'candidate-tools.py'
        helper.write_text(overrides.get('docker/local/tools.py', (root / 'docker/local/tools.py').read_text()))
        task.copy_file(helper, '/tmp')
        copy_runtime(runtime, root, overrides)
        authority = Authority(client, task, settings, run, system, issue)
        process = subprocess.Popen(['docker', 'exec', '-i', '-w', '/workspace', runtime.name,
                                    'python', '/tmp/runner.py'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.stdin.write((json.dumps({'settings': settings, 'issue': issue, 'system': system}) + '\n').encode())
            process.stdin.flush()
            result = bridge(process, authority, run / 'runtime-stderr.log')
            if result['reason'] == 'submitted':
                (run / 'patch.diff').write_text(authority.last_patch)
            return result
        finally:
            # The container context also kills any descendants, without host mounts/socket access.
            subprocess.run(['docker', 'kill', runtime.name], capture_output=True, timeout=15)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
