import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.agent import AgentLoop
from gemma_lab.tools import validate

class FakeSandbox:
    def __init__(self):
        self.calls = []
    def call(self, name, args, timeout=None):
        self.calls.append((name, args))
        return {'output': 'ok'}
    def patch(self):
        return 'diff --git a/x b/x\n'

class FakeClient:
    def __init__(self, calls):
        self.calls = iter(calls)
        self.histories = []
    def complete(self, messages, tools, timeout):
        self.histories.append(messages)
        name, args = next(self.calls)
        return {'choices': [{'finish_reason': 'tool_calls', 'message': {'content': None, 'tool_calls': [
            {'id': str(len(self.histories)), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}
        ]}}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.settings = {'max_turns': 5, 'max_tool_calls': 5, 'time_limit_seconds': 30, 'history_char_limit': 3000}

    def test_unknown_tool_is_not_executed_and_model_can_recover(self):
        client = FakeClient([('host_shell', {'command': 'bad'}), ('submit_patch', {})])
        sandbox = FakeSandbox()
        result = AgentLoop(client, sandbox, self.settings, self.run).solve('fix issue', 'use tools')
        self.assertEqual(result['reason'], 'submitted')
        self.assertEqual(sandbox.calls, [])
        self.assertTrue((self.run / 'patch.diff').exists())
        self.assertIn('Unknown tool', client.histories[1][-1]['content'])

    def test_budget_stops_execution_and_does_not_submit(self):
        self.settings['max_tool_calls'] = 1
        sandbox = FakeSandbox()
        result = AgentLoop(FakeClient([('run_command', {'command': 'ls'})]), sandbox,
                           self.settings, self.run).solve('fix issue', 'use tools')
        self.assertEqual(result['reason'], 'tool_limit')
        self.assertEqual(len(sandbox.calls), 1)
        self.assertFalse((self.run / 'patch.diff').exists())

    def test_passing_rerun_clears_stale_failure_and_edit_invalidates_verification(self):
        settings = dict(self.settings, verification_command='python -m unittest')
        agent = AgentLoop(FakeClient([]), FakeSandbox(), settings, self.run)
        args = {'command': 'python -m unittest'}
        agent.remember_result('run_command', args, {'exit_code': 1, 'output': 'FAILED'})
        self.assertIsNotNone(agent.last_failure)
        agent.remember_result('run_command', args, {'exit_code': 0, 'output': 'OK'})
        self.assertIsNone(agent.last_failure)
        self.assertTrue(agent.verification_passed)
        agent.remember_result('edit_file', {'filepath': 'module.py'}, {'replacements': 1})
        self.assertFalse(agent.verification_passed)

    def test_request_timeout_at_task_deadline_is_an_incomplete_run(self):
        class DeadlineClient:
            def complete(inner, messages, tools, timeout):
                agent.deadline = 0
                raise TimeoutError('timed out')
        agent = AgentLoop(DeadlineClient(), FakeSandbox(), self.settings, self.run)
        result = agent.solve('fix issue', 'use tools')
        self.assertEqual(result['reason'], 'time_limit')
        self.assertFalse((self.run / 'patch.diff').exists())
        self.assertIn('request_timeout', (self.run / 'trajectory.jsonl').read_text())

    def test_invalid_tool_types_rejected(self):
        for name, args in [('run_command', {'command': 1}), ('get_status', {'secret': 1}),
                           ('read_file', {'filepath': 'x', 'start_line': True})]:
            with self.assertRaises(ValueError):
                validate(name, args)

    def test_submission_review_gate_and_public_test_failure(self):
        sandbox = FakeSandbox()
        sandbox.run_command = lambda command, timeout=None: {'exit_code': 1, 'timed_out': False, 'output': 'test failed'}
        settings = dict(self.settings, review_before_submit=True, require_regression_tests=True,
                        verification_command='python -m unittest')
        agent = AgentLoop(FakeClient([]), sandbox, settings, self.run)
        implementation = 'diff --git a/module.py b/module.py\n'
        self.assertTrue(agent.submission_gate(implementation)['review_required'])
        self.assertIn('Add regression', agent.submission_gate(implementation)['error'])
        with_test = implementation + 'diff --git a/tests/test_bug.py b/tests/test_bug.py\n'
        rejected = agent.submission_gate(with_test)
        self.assertIn('Public verification failed', rejected['error'])
        self.assertFalse((self.run / 'patch.diff').exists())

    def test_truncated_tool_response_is_logged_but_not_executed(self):
        class TruncatedClient(FakeClient):
            def complete(self, messages, tools, timeout):
                response = super().complete(messages, tools, timeout)
                if len(self.histories) == 1:
                    response['choices'][0]['finish_reason'] = 'length'
                return response
        client = TruncatedClient([('run_command', {'command': 'never execute'}), ('submit_patch', {})])
        sandbox = FakeSandbox()
        result = AgentLoop(client, sandbox, self.settings, self.run).solve('fix issue', 'use tools')
        self.assertEqual(result['reason'], 'submitted')
        self.assertEqual(sandbox.calls, [])
        self.assertIn('truncated', (self.run / 'trajectory.jsonl').read_text())

class ContainerToolTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'docker/local/tools.py'
        spec = importlib.util.spec_from_file_location('container_tools', path)
        self.tools = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tools)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.root.mkdir()
        self.tools.ROOT = self.root

    def test_file_tools_cannot_escape_workspace_through_symlinks(self):
        (self.root / 'escape').symlink_to(self.root.parent)
        for path in ['../secret', 'escape/secret', '/etc/passwd']:
            with self.assertRaises(ValueError):
                self.tools.dispatch('write_file', {'filepath': path, 'content': 'bad'}, 1, 100)

    def test_edit_requires_unique_match(self):
        target = self.root / 'x'
        target.write_text('duplicate duplicate')
        with self.assertRaises(ValueError):
            self.tools.dispatch('edit_file', {'filepath': 'x', 'old_string': 'duplicate', 'new_string': 'fixed'}, 1, 100)
        self.assertEqual(target.read_text(), 'duplicate duplicate')

    def test_command_timeout_and_bounded_output(self):
        output = self.tools.command("printf '123456789'", 1, 4)
        self.assertEqual(output['output'], '1234')
        self.assertTrue(output['truncated'])
        timeout = self.tools.command('sleep 5', 0.1, 100)
        self.assertTrue(timeout['timed_out'])
        self.assertNotEqual(timeout['exit_code'], 0)

if __name__ == '__main__':
    unittest.main()
