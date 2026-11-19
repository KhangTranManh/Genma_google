"""Progress-bound orchestration, isolated from the unchanged legacy AgentLoop."""
import hashlib
import json
import shlex
import time
from .agent import AgentLoop
from .tools import TOOLS, validate


def is_test_path(path):
    return path.startswith('tests/') or '/tests/' in path or path.rsplit('/', 1)[-1].startswith('test_') or path.endswith('_test.py')


def test_command(command):
    try:
        words = shlex.split(command)
    except ValueError:
        return False
    return (len(words) >= 3 and words[0] in ('python', 'python3') and words[1] == '-m' and words[2] in ('unittest', 'pytest')) or bool(words and words[0] == 'pytest')

def test_identity(command):
    words = shlex.split(command)
    if words[0] in ('python', 'python3'):
        words = words[2:]
    return json.dumps([word for word in words if word not in ('-q', '-v', '-vv', '--quiet', '--verbose')])

def verification_matches(command, configured, revision=1):
    """V2 permits only interpreter aliases/verbosity changes, preserving all targets."""
    if command == configured:
        return True
    if revision != 2 or not command or not configured:
        return False
    try:
        return test_command(command) and test_command(configured) and test_identity(command) == test_identity(configured)
    except ValueError:
        return False


class ProgressState:
    def __init__(self, repeat_limit=2, stagnation_limit=16):
        self.repeat_limit, self.stagnation_limit = repeat_limit, stagnation_limit
        self.version = None
        self.paths = []
        self.seen = {}
        self.blocked = self.bad_edits = self.stagnant = 0
        self.total_blocked = 0
        self.verified_version = self.failed_version = None
        self.observations = 0
        self.cached_files = {}

    def observe(self, patch):
        self.observations += 1
        version = hashlib.sha256(patch.encode()).hexdigest()
        changed = version != self.version
        if changed:
            self.version = version
            self.paths = [line.split(' b/', 1)[1] for line in patch.splitlines() if line.startswith('diff --git ') and ' b/' in line]
            self.seen.clear()
            self.blocked = self.bad_edits = self.stagnant = 0
            self.verified_version = self.failed_version = None
        return changed

    @property
    def phase(self):
        source = any(not is_test_path(path) for path in self.paths)
        tests = any(is_test_path(path) for path in self.paths)
        if self.version is not None and self.verified_version == self.version:
            return 'review_submit'
        if (self.version is not None and self.failed_version == self.version) or (tests and not source):
            return 'repair'
        if source and not tests:
            return 'add_regression_tests'
        if source and tests:
            return 'verify'
        return 'inspect_reproduce'

    def before(self, name, arguments):
        if name == 'submit_patch':
            return None
        # Equivalent test invocations share a key so changing flags cannot reset a test loop.
        key = 'verification:' + test_identity(arguments['command']) if name == 'run_command' and test_command(arguments.get('command', '')) else name + ':' + json.dumps(arguments, sort_keys=True)
        count = self.seen.get(key, 0) + 1
        self.seen[key] = count
        if count > self.repeat_limit:
            self.blocked += 1
            self.total_blocked += 1
            return {'error': 'Repeated operation without a workspace change. The operation was not executed.', 'executed': False,
                    'phase': self.phase, 'next_action': self.guidance()}
        return None

    def result(self, name, arguments, result, changed, exact_verification):
        self.stagnant = 0 if changed else self.stagnant + 1
        executed = result.get('executed', True)
        if executed and name == 'edit_file' and result.get('error'):
            self.bad_edits += 1
        if executed and name == 'read_file' and result.get('content') and not is_test_path(arguments.get('filepath', '')):
            cached = {'content': result['content'][:3000],
                      'truncated': result.get('truncated', False) or len(result['content']) > 3000
                                   or bool(arguments.get('start_line') or arguments.get('end_line'))}
            if self.cached_files.get(arguments['filepath']) != cached:
                self.stagnant = self.blocked = 0
            self.cached_files[arguments['filepath']] = cached
        if executed and name == 'run_command' and test_command(arguments.get('command', '')):
            if result.get('exit_code') != 0 or result.get('timed_out'):
                if self.failed_version != self.version:
                    self.stagnant = 0
                self.failed_version = self.version
                self.verified_version = None
            elif exact_verification and not changed:
                self.failed_version = None
                self.verified_version = self.version
                self.stagnant = 0

    def guidance(self):
        if self.phase == 'review_submit':
            return 'Tests passed for the current code. Review the displayed diff and call submit_patch. Do not rerun unchanged checks.'
        if self.bad_edits >= 2:
            return 'Exact edits failed twice. Use write_file with complete valid file text, without line-number labels or double escaping.'
        if self.phase == 'repair':
            return 'The failure is already reproduced. Change the implementation next; rerunning unchanged tests does not fix it.'
        if self.phase == 'add_regression_tests':
            return 'Add regression tests for the issue, preserving existing tests.'
        if self.phase == 'verify':
            return 'Run the configured verification command on this code version.'
        return 'Inspect the relevant implementation and tests, then reproduce and fix the issue.'

    def allowed(self):
        if self.phase == 'review_submit':
            return {'submit_patch', 'get_status'}
        if self.bad_edits >= 2:
            allowed = {'write_file', 'get_status'}
            if not self.cached_files or any(item['truncated'] for item in self.cached_files.values()):
                allowed.add('read_file')
            return allowed
        if self.blocked >= 2 and self.phase in ('repair', 'add_regression_tests', 'verify'):
            return {'edit_file', 'write_file', 'get_status'}
        return {item['function']['name'] for item in TOOLS}

    def stalled(self):
        return self.blocked >= 4 or self.stagnant >= self.stagnation_limit

    def export(self):
        return {'phase': self.phase, 'workspace_version': self.version, 'changed_files': self.paths,
                'blocked_repeats': self.blocked, 'blocked_repeats_total': self.total_blocked, 'failed_edits': self.bad_edits, 'stagnant_actions': self.stagnant,
                'verification_bound_to_current_code': self.version is not None and self.verified_version == self.version,
                'next_action': self.guidance(), 'observations': self.observations,
                'implementation_context': dict(list(self.cached_files.items())[-2:])}


class ProgressAgent(AgentLoop):
    def __init__(self, client, sandbox, settings, run):
        super().__init__(client, sandbox, settings, run)
        self.progress = ProgressState(settings.get('repeat_limit', 2), settings.get('stagnation_limit', 16))
        mode = settings.get('progress_mode', 'detect_only')
        if mode not in ('detect_only', 'finish_verified'):
            raise ValueError('Unknown progress_mode')
        self.auto_finish = mode == 'finish_verified'
        self.checked_versions = set()
        self.harness_checks = 0
        self.origin = None
        self.revision = settings.get('progress_revision', 1)
        if self.revision not in (1, 2):
            raise ValueError('Unknown progress_revision')

    def persist(self):
        (self.run / 'progress-state.json').write_text(json.dumps(self.progress.export(), indent=2) + '\n')

    def snapshot(self):
        patch = self.sandbox.patch()
        changed = self.progress.observe(patch)
        self.persist()
        return patch, changed

    def verified_finish(self, patch):
        if time.monotonic() >= self.deadline or self.progress.phase not in ('verify', 'review_submit'):
            return None
        if not any(is_test_path(path) for path in self.progress.paths) or not any(not is_test_path(path) for path in self.progress.paths):
            return None
        version = self.progress.version
        if version in self.checked_versions and self.progress.phase != 'review_submit':
            return None
        self.checked_versions.add(version)
        verify = self.settings.get('verification_command')
        if not verify:
            return None
        self.harness_checks += 1
        result = self.sandbox.run_command(verify, timeout=max(1, self.deadline - time.monotonic()))
        self.event('harness_verification', command=verify, result=result, version=version)
        (self.run / 'public-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
        current, changed = self.snapshot()
        self.progress.result('run_command', {'command': verify}, result, changed, exact_verification=True)
        if result.get('exit_code') != 0 or result.get('timed_out') or self.progress.version != version or time.monotonic() >= self.deadline:
            return None
        # Host review and authoritative configured tests precede harness-origin submission.
        review = {'workspace_version': version, 'changed_files': self.progress.paths, 'patch_sha256': hashlib.sha256(current.encode()).hexdigest(),
                  'diff': current, 'origin': 'harness'}
        (self.run / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
        self.review_requested = True
        gate = super().submission_gate(current)
        self.event('harness_submission_gate', result=gate)
        final_patch, _ = self.snapshot()
        if gate.get('submitted') and self.progress.version == version and final_patch == current and time.monotonic() < self.deadline:
            (self.run / 'patch.diff').write_text(current)
            self.origin = 'harness'
            return self.finish('harness_submitted')
        return None

    def solve(self, issue, system):
        initial = [{'role': 'system', 'content': system}, {'role': 'user', 'content': issue}]
        if sum(len(m['content']) for m in initial) > self.settings['history_char_limit'] // 2:
            raise ValueError('Task/system prompt exceeds local context allowance')
        groups = []
        self.snapshot()
        for turn in range(1, self.settings['max_turns'] + 1):
            if time.monotonic() >= self.deadline:
                return self.finish('time_limit')
            if self.calls >= self.settings['max_tool_calls']:
                return self.finish('tool_limit')
            self.turn = turn
            memory = {'runtime_state': self.progress.export(), 'last_error': self.last_failure, 'budget': self.status()}
            if self.revision == 2:
                memory['verification_command'] = self.settings.get('verification_command')
            prefix = initial + [{'role': 'user', 'content': json.dumps(memory)}]
            messages = prefix + [item for group in groups for item in group]
            while len(json.dumps(messages)) > self.settings['history_char_limit'] and len(groups) > 1:
                groups.pop(0)
                messages = prefix + [item for group in groups for item in group]
            allowed = self.progress.allowed()
            try:
                response = self.client.complete(messages, [item for item in TOOLS if item['function']['name'] in allowed],
                                                timeout=max(1, self.deadline - time.monotonic()))
            except TimeoutError:
                if time.monotonic() >= self.deadline:
                    return self.finish('time_limit')
                raise
            self.event('response', response=response)
            for key in self.usage:
                self.usage[key] += response.get('usage', {}).get(key, 0)
            if response['choices'][0]['finish_reason'] == 'length':
                groups.append([{'role': 'user', 'content': 'Response truncated. Use one concise tool call.'}])
                continue
            message = response['choices'][0]['message']
            calls = message.get('tool_calls') or []
            assistant = {'role': 'assistant', 'content': message.get('content')}
            if message.get('reasoning'):
                assistant['reasoning'] = message['reasoning']
            if calls:
                assistant['tool_calls'] = calls
            group = [assistant]
            groups.append(group)
            self.event('turn', turn=turn, tool_calls=len(calls), progress=self.progress.export())
            if not calls:
                self.progress.stagnant += 1
                group.append({'role': 'user', 'content': self.progress.guidance()})
            for call in calls:
                name, arguments = call['function']['name'], None
                self.event('tool_call', turn=turn, name=name, raw_arguments=call['function']['arguments'])
                if time.monotonic() >= self.deadline or self.calls >= self.settings['max_tool_calls']:
                    result = {'error': 'Execution budget exhausted', 'executed': False}
                else:
                    self.calls += 1
                    try:
                        arguments = json.loads(call['function']['arguments'])
                        validate(name, arguments)
                        if name not in allowed:
                            self.progress.blocked += 1
                            self.progress.total_blocked += 1
                            result = {'error': 'Tool unavailable in the current progress phase.', 'executed': False, 'next_action': self.progress.guidance()}
                        else:
                            result = self.progress.before(name, arguments)
                            if result is None:
                                if name == 'get_status':
                                    result = dict(self.status(), progress=self.progress.export())
                                elif name == 'submit_patch':
                                    patch, _ = self.snapshot()
                                    result = super().submission_gate(patch)
                                    if result.get('review_required'):
                                        result['diff_for_review'] = patch[:4000]
                                        result['next_action'] = 'Review the shown diff and call submit_patch again.'
                                    if result.get('submitted'):
                                        (self.run / 'patch.diff').write_text(patch)
                                        self.origin = 'model'
                                else:
                                    result = self.sandbox.call(name, arguments, timeout=max(1, self.deadline - time.monotonic()))
                    except (ValueError, KeyError) as error:
                        result = {'error': str(error), 'executed': False}
                patch, changed = self.snapshot()
                args = arguments if isinstance(arguments, dict) else {}
                self.remember_result(name, args, result)
                self.progress.result(name, args, result, changed,
                                     exact_verification=name == 'run_command' and verification_matches(args.get('command'), self.settings.get('verification_command'), self.revision))
                if self.progress.verified_version == self.progress.version:
                    self.last_failure = None
                self.event('tool_result', name=name, result=result)
                self.persist()
                self.event('progress', **self.progress.export())
                group.append({'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(result)})
                if self.origin == 'model':
                    return self.finish('submitted')
                if self.auto_finish:
                    done = self.verified_finish(patch)
                    if done:
                        return done
            if self.progress.stalled():
                return self.finish('stalled')
        return self.finish('turn_limit')

    def finish(self, reason):
        try:
            patch = self.sandbox.patch()
            if reason not in ('submitted', 'harness_submitted') and patch.strip():
                (self.run / 'recovered.diff').write_text(patch)
        except Exception as error:
            self.event('recovery_failed', error=str(error))
        self.persist()
        result = {'reason': reason, 'turns': self.turn, 'tool_calls': self.calls, 'usage': self.usage,
                  'submission_origin': self.origin, 'progress': self.progress.export(), 'harness_verifications': self.harness_checks}
        self.event('finished', **result)
        return result
