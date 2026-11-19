import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
from gemma_lab.config import load
from gemma_lab.local import evaluate
from workflow_lab import ALLOWED, candidate_decision, make_repository, parse_edits
from workflow_rpc import Authority, BudgetExceeded, run_runtime, validate_runtime, limited_exec
from gemma_lab.sandbox import DockerSandbox

class WorkflowCodeTests(unittest.TestCase):
    def test_source_patch_cannot_edit_evaluator_or_escape_paths(self):
        source = {name: 'value = 1\n' for name in ALLOWED}
        for path in ('examples/evaluation/test.py', '../escape.py', 'submission/prompts/system.md'):
            with self.assertRaisesRegex(ValueError, 'permitted'):
                parse_edits({'edits': [{'path': path, 'old_string': 'value = 1', 'new_string': 'value = 2'}], 'rationale': 'x'}, source)

    def test_source_parsing_never_executes_candidate_on_host(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / 'must-not-exist'
            source = {name: 'value = 1\n' for name in ALLOWED}
            text = f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("bad")\n'
            candidate = parse_edits({'edits': [{'path': ALLOWED[0], 'old_string': 'value = 1\n', 'new_string': text}], 'rationale': 'test'}, source)
            self.assertIn('write_text', candidate[ALLOWED[0]])
            self.assertFalse(sentinel.exists())

    def test_invalid_or_repository_specific_python_is_rejected(self):
        source = {name: 'value = 1\n' for name in ALLOWED}
        for text in ('def broken(', 'urlkit = 1'):
            with self.assertRaises((ValueError, SyntaxError)):
                parse_edits({'edits': [{'path': ALLOWED[0], 'old_string': 'value = 1\n', 'new_string': text}], 'rationale': 'x'}, source)

    def test_host_controls_model_calls_and_frozen_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Mock()
            task._exec.return_value = subprocess.CompletedProcess([], 0, b'a' * 40, b'')
            client = Mock()
            authority = Authority(client, task, {'max_turns': 0, 'max_tool_calls': 0, 'time_limit_seconds': 10}, Path(directory), 'frozen', 'issue')
            with self.assertRaises(BudgetExceeded):
                authority.dispatch({'operation': 'complete', 'messages': []})
            client.complete.assert_not_called()
            authority.settings['max_turns'] = 1
            with self.assertRaisesRegex(ValueError, 'frozen system'):
                authority.dispatch({'operation': 'complete', 'messages': [{'role': 'system', 'content': 'modified'}]})
            result = authority.dispatch({'operation': 'finish', 'outcome': {'reason': 'submitted'}})
            self.assertEqual(result['reason'], 'empty_patch')

    def test_snapshots_cannot_bypass_host_tool_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Mock()
            task._exec.return_value = subprocess.CompletedProcess([], 0, b'a' * 40, b'')
            authority = Authority(Mock(), task, {'max_turns': 5, 'max_tool_calls': 0, 'time_limit_seconds': 10}, Path(directory), 'system', 'issue')
            with self.assertRaisesRegex(BudgetExceeded, 'tool_limit'):
                authority.dispatch({'operation': 'snapshot'})

    def test_a_failed_candidate_cannot_be_promoted(self):
        baseline = {'status': 'local_pass', 'elapsed_seconds': 100, 'agent': {'usage': {'completion_tokens': 100}}}
        failed = dict(baseline, status='local_fail', elapsed_seconds=1)
        self.assertEqual(candidate_decision(baseline, failed, True), 'rejected_task_result')
        self.assertEqual(candidate_decision(baseline, baseline, False), 'rejected_validation')
        faster = dict(baseline, elapsed_seconds=80)
        self.assertEqual(candidate_decision(baseline, faster, True), 'provisional_improvement')
        self.assertEqual(candidate_decision(baseline, baseline, True), 'no_measured_improvement')

@unittest.skipUnless(os.environ.get('GEMMA_DOCKER_TESTS') == '1', 'enable Docker integration explicitly')
class WorkflowRuntimeIntegrationTests(unittest.TestCase):
    def test_untrusted_process_output_and_silence_are_bounded(self):
        project = load(ROOT / 'configs/project.toml')
        with DockerSandbox(project.raw['workflow']['image']) as container:
            with self.assertRaisesRegex(BudgetExceeded, 'tool_output_limit'):
                limited_exec(container, ['python', '-c', 'print("x" * 50000)'], limit=1000)
            with self.assertRaisesRegex(BudgetExceeded, 'tool_timeout'):
                limited_exec(container, ['python', '-c', 'import time; time.sleep(10)'], timeout=0.1)

    def test_original_runtime_passes_frozen_unit_validation_in_container(self):
        project = load(ROOT / 'configs/project.toml')
        result = validate_runtime(ROOT, project.raw['workflow'], {})
        self.assertEqual(result['exit_code'], 0, result['output'])

    def test_rpc_runtime_produces_real_patch_without_host_code_execution(self):
        project = load(ROOT / 'configs/project.toml')
        settings = dict(project.raw['workflow'], verification_command='python -m unittest discover -s tests -v')
        calls = [
            ('edit_file', {'filepath': 'urlkit/__init__.py',
                'old_string': '    query = dict(parse_qsl(parts.query))\n    query.update(params)',
                'new_string': '    query = parse_qsl(parts.query, keep_blank_values=True)\n    query.extend(params.items() if isinstance(params, dict) else params)'}),
            ('write_file', {'filepath': 'tests/test_new.py', 'content': 'import unittest\nfrom urlkit import append_query\nclass New(unittest.TestCase):\n def test_blank(self):\n  self.assertEqual(append_query("/?x=", {}), "/?x=")\n'}),
            ('run_command', {'command': settings['verification_command']}),
            ('submit_patch', {}), ('run_command', {'command': 'git diff'}), ('submit_patch', {})]
        class Client:
            def complete(self, messages, tools, timeout):
                name, arguments = calls.pop(0)
                return {'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                    'tool_calls': [{'id': str(len(calls)), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'source'
            source.mkdir()
            task = make_repository(project, source)
            run = folder / 'run'
            run.mkdir()
            result = run_runtime(ROOT, source, task['base_commit'], settings, Client(), 'issue', 'frozen system', run, {})
            self.assertEqual(result['reason'], 'submitted')
            patch = (run / 'patch.diff').read_text()
            self.assertIn('keep_blank_values=True', patch)
            verdict = evaluate(settings, source, task['base_commit'], patch, ROOT / 'examples/evaluation/test_urlkit.py')
            self.assertEqual(verdict['exit_code'], 0, verdict['output'])
            self.assertIn('query = dict', (source / 'urlkit/__init__.py').read_text())

    def test_candidate_import_writes_only_inside_runtime_container(self):
        project = load(ROOT / 'configs/project.toml')
        settings = dict(project.raw['workflow'], time_limit_seconds=10)
        sentinel = Path('/tmp') / ('gemma-candidate-' + uuid.uuid4().hex)
        code = f'''from pathlib import Path
Path({str(sentinel)!r}).write_text("container only")
class AgentLoop:
 def __init__(self, *args): pass
 def solve(self, *args): return {{"reason": "runtime_error"}}
'''
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'source'
            source.mkdir()
            task = make_repository(project, source)
            run = folder / 'run'
            run.mkdir()
            result = run_runtime(ROOT, source, task['base_commit'], settings, Mock(), 'issue', 'system', run,
                                 {'src/gemma_lab/agent.py': code})
            self.assertEqual(result['reason'], 'runtime_error')
            self.assertFalse(sentinel.exists())

if __name__ == '__main__':
    unittest.main()
