import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gemma_lab.config import load
from gemma_lab.progress_agent import ProgressState, ProgressAgent
from gemma_lab.sandbox import DockerSandbox
from gemma_lab.local import evaluate
from workflow_lab import make_repository

ROOT = Path(__file__).resolve().parents[1]
DIFF = 'diff --git a/module.py b/module.py\n+fixed\ndiff --git a/tests/test_x.py b/tests/test_x.py\n+test\n'

class ProgressTests(unittest.TestCase):
    def test_repeated_actions_are_blocked_only_for_unchanged_workspace(self):
        state = ProgressState()
        state.observe('')
        args = {'filepath': 'module.py'}
        self.assertIsNone(state.before('read_file', args))
        self.assertIsNone(state.before('read_file', args))
        self.assertIn('not executed', state.before('read_file', args)['error'])
        state.observe(DIFF)
        self.assertIsNone(state.before('read_file', args))
        self.assertEqual(state.total_blocked, 1)

    def test_different_test_targets_are_not_false_positive_repeats(self):
        state = ProgressState(repeat_limit=1)
        state.observe('')
        self.assertIsNone(state.before('run_command', {'command': 'python -m unittest tests.test_a -v'}))
        self.assertIsNone(state.before('run_command', {'command': 'python -m unittest tests.test_b -v'}))
        self.assertIn('error', state.before('run_command', {'command': 'python3 -m unittest tests.test_a -q'}))

    def test_new_implementation_information_resets_stagnation(self):
        state = ProgressState()
        state.observe('')
        state.stagnant = 15
        state.result('read_file', {'filepath': 'module.py'}, {'content': '1: value = 1'}, False, False)
        self.assertEqual(state.stagnant, 0)

    def test_test_success_is_bound_to_the_current_code_version(self):
        state = ProgressState()
        self.assertEqual(state.phase, 'inspect_reproduce')
        state.observe(DIFF)
        self.assertEqual(state.phase, 'verify')
        state.result('run_command', {'command': 'python -m unittest'}, {'exit_code': 0}, False, True)
        self.assertEqual(state.phase, 'review_submit')
        state.observe(DIFF + '+new change\n')
        self.assertEqual(state.phase, 'verify')
        self.assertIsNone(state.verified_version)

    def test_partial_test_success_is_not_full_verification(self):
        state = ProgressState()
        state.observe(DIFF)
        state.result('run_command', {'command': 'python -m unittest tests.one'}, {'exit_code': 0}, False, False)
        self.assertEqual(state.phase, 'verify')
        state.result('run_command', {'command': 'python -m unittest'}, {'exit_code': 1}, False, True)
        self.assertEqual(state.phase, 'repair')

    def test_suppressed_test_calls_cannot_erase_valid_verification(self):
        state = ProgressState()
        state.observe(DIFF)
        args = {'command': 'python -m unittest'}
        state.result('run_command', args, {'exit_code': 0}, False, True)
        state.result('run_command', args, {'error': 'suppressed repeat', 'executed': False}, False, True)
        self.assertEqual(state.phase, 'review_submit')

    def test_test_process_that_changes_source_does_not_verify_the_new_version(self):
        state = ProgressState()
        state.observe(DIFF)
        state.result('run_command', {'command': 'python -m unittest'}, {'exit_code': 0}, True, True)
        self.assertEqual(state.phase, 'verify')

    def test_failed_edits_switch_to_a_different_editing_action(self):
        state = ProgressState()
        state.observe(DIFF)
        for _ in range(2):
            state.result('edit_file', {'filepath': 'module.py'}, {'error': 'not found'}, False, False)
        self.assertIn('read_file', state.allowed())
        state.cached_files['module.py'] = {'content': '1: value = 1', 'truncated': False}
        self.assertEqual(state.allowed(), {'write_file', 'get_status'})

    def test_tests_only_change_requires_an_implementation_fix(self):
        state = ProgressState()
        state.observe('diff --git a/tests/test_x.py b/tests/test_x.py\n+test\n')
        self.assertEqual(state.phase, 'repair')
        self.assertIn('Change the implementation', state.guidance())

@unittest.skipUnless(os.environ.get('GEMMA_DOCKER_TESTS') == '1', 'enable Docker integration')
class ProgressIntegrationTests(unittest.TestCase):
    def run_policy(self, mode, revision=1):
        project = load(ROOT / 'configs/project.toml')
        settings = dict(project.raw['workflow'], progress_mode=mode, progress_revision=revision, verification_command='python -m unittest discover -s tests -v')
        calls = [
            ('edit_file', {'filepath': 'urlkit/__init__.py',
                          'old_string': '    query = dict(parse_qsl(parts.query))\n    query.update(params)',
                          'new_string': '    query = parse_qsl(parts.query, keep_blank_values=True)\n    query.extend(params.items() if isinstance(params, dict) else params)'}),
            ('write_file', {'filepath': 'tests/test_new.py', 'content': 'import unittest\nfrom urlkit import append_query\nclass New(unittest.TestCase):\n def test_blank(self):\n  self.assertEqual(append_query("/?x=", {}), "/?x=")\n'}),
            ('run_command', {'command': settings['verification_command'].replace('python ', 'python3 ') if revision == 2 else settings['verification_command']}), ('submit_patch', {}), ('submit_patch', {})]
        class Client:
            def complete(self, messages, tools, timeout):
                name, args = calls.pop(0)
                if revision == 2 and name == 'submit_patch':
                    assert {item['function']['name'] for item in tools} == {'submit_patch', 'get_status'}, 'Equivalent verification was not recognized'
                return {'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
                    'tool_calls': [{'id': str(len(calls)), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
        with tempfile.TemporaryDirectory() as directory:
            source, run = Path(directory) / 'source', Path(directory) / 'run'
            source.mkdir(); run.mkdir()
            task = make_repository(project, source)
            with DockerSandbox(settings['image'], 20, 4000) as sandbox:
                sandbox.checkout(source, task['base_commit'])
                result = ProgressAgent(Client(), sandbox, settings, run).solve('fix issue', 'fixed system')
            self.assertEqual(result['reason'], 'harness_submitted' if mode == 'finish_verified' else 'submitted')
            self.assertEqual(result['submission_origin'], 'harness' if mode == 'finish_verified' else 'model')
            patch = (run / 'patch.diff').read_text()
            verdict = evaluate(settings, source, task['base_commit'], patch, ROOT / 'examples/evaluation/test_urlkit.py')
            self.assertEqual(verdict['exit_code'], 0, verdict['output'])
            if mode == 'finish_verified':
                self.assertEqual(result['turns'], 2)
                self.assertTrue((run / 'review.json').exists())
            return result

    def test_harness_can_finish_a_verified_patch_without_a_model_submit_call(self):
        self.run_policy('finish_verified')

    def test_detect_only_mode_still_requires_explicit_model_submission(self):
        self.run_policy('detect_only')

    def test_v2_equivalent_interpreter_verification_allows_autonomous_completion(self):
        self.run_policy('detect_only', revision=2)

if __name__ == '__main__':
    unittest.main()
