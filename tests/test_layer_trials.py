import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from gemma_lab.config import load
from gemma_lab.progress_agent import verification_matches, ProgressState


class LayerTrialTests(unittest.TestCase):
    def test_v2_recognizes_same_suite_but_never_partial_or_shell_commands(self):
        configured = 'python -m unittest discover -s tests -v'
        self.assertFalse(verification_matches('python3 -m unittest discover -s tests -v', configured))
        self.assertTrue(verification_matches('python3 -m unittest discover -s tests -q', configured, 2))
        for command in ['python -m unittest tests.one -v', 'python -m unittest discover -s other -v',
                        'python -m unittest discover -s tests -v; true',
                        'python -m unittest discover -s tests -v && true',
                        'python -m unittest discover -s tests -v -k one', 'echo hi', 'python "']:
            self.assertFalse(verification_matches(command, configured, 2), command)

    def test_recognized_verification_unlocks_submit_and_changes_invalidate_it(self):
        state = ProgressState()
        patch = 'diff --git a/a.py b/a.py\n+x\ndiff --git a/tests/test_a.py b/tests/test_a.py\n+x\n'
        state.observe(patch)
        valid = verification_matches('python3 -m unittest discover -s tests -v', 'python -m unittest discover -s tests -v', 2)
        state.result('run_command', {'command': 'python3 -m unittest discover -s tests -v'}, {'exit_code': 0}, False, valid)
        self.assertEqual(state.allowed(), {'submit_patch', 'get_status'})
        state.observe(patch + '+change\n')
        self.assertNotEqual(state.phase, 'review_submit')

    def test_each_layer_changes_only_its_declared_setting(self):
        control = load(ROOT / 'configs/experiments/layers_control.toml').raw
        for name, changed in [('prompt', 'system_prompt'), ('code', 'progress_revision'), ('runtime', 'history_char_limit')]:
            candidate = load(ROOT / f'configs/experiments/layers_{name}.toml').raw
            self.assertEqual(candidate['automation']['model_order'], ['12b', '31b'])
            self.assertEqual(candidate['automation']['strategy'], candidate['experiment']['method'])
            self.assertEqual(candidate['serving'], control['serving'])
            diff = {key for key in candidate['workflow'] if candidate['workflow'][key] != control['workflow'][key]}
            self.assertEqual(diff, {changed})
            self.assertEqual(candidate['workflow']['progress_mode'], 'detect_only')

class LayerReportTests(unittest.TestCase):
    def test_matching_controls_and_failed_candidate_are_not_reported_as_gain(self):
        from layer_report import generate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'configs').mkdir()
            (root / 'configs/study.toml').write_text('[layer_comparison]\nexperiments=["layers_control_v1","layers_code_v1"]\nmodels=["12b"]\n')
            for ident, revision, status in [('layers_control_v1', 1, 'local_pass'), ('layers_code_v1', 2, 'incomplete')]:
                folder = root / 'runs' / ident;folder.mkdir(parents=True)
                (folder / 'manifest.json').write_text(json.dumps({'experiment': {'id': ident}, 'model_key': '12b',
                    'status': status, 'workflow_sha256': 'fixed', 'prompt_sha256': 'fixed',
                    'config': {'ablation': {'layer': 'code' if revision == 2 else 'control'}, 'serving': {}},
                    'workflow': {'progress_revision': revision, 'system_prompt': '/same'},
                    'agent': {'submission_origin': 'model' if status == 'local_pass' else None}}))
                if status == 'local_pass':
                    (folder / 'evaluation.json').write_text(json.dumps({'exit_code': 0, 'output': 'test_a ... ok\nRan 1 test\nOK'}))
                else:
                    (folder / 'recovered-evaluation.json').write_text(json.dumps({'exit_code': 0, 'output': 'test_a ... ok\nRan 1 test\nOK'}))
            data = generate(root)
            self.assertEqual(data['warnings'], [])
            self.assertIn('Regression', data['assessments'][0]['finding'])
            self.assertFalse(data['rows'][0]['autonomous_pass'] if data['rows'][0]['status'] == 'incomplete' else data['rows'][1]['autonomous_pass'])


    def test_combined_configs_hold_code_and_runtime_fixed(self):
        control = load(ROOT / 'configs/experiments/combined_control.toml').raw
        candidate = load(ROOT / 'configs/experiments/combined_prompt.toml').raw
        self.assertEqual(control['workflow']['progress_revision'], 2)
        self.assertEqual(candidate['workflow']['progress_revision'], 2)
        self.assertEqual(control['automation']['model_order'], ['12b', '31b'])
        self.assertEqual(control['serving'], candidate['serving'])
        differences = {k for k in candidate['workflow'] if candidate['workflow'][k] != control['workflow'][k]}
        self.assertEqual(differences, {'system_prompt'})

    def test_combined_report_keeps_code_revision_in_controls(self):
        import hashlib
        from layer_report import generate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'configs').mkdir()
            (root / 'configs/study.toml').write_text('[combined_comparison]\nexperiments=["combined_control_v1","combined_prompt_v1"]\nmodels=["12b"]\n')
            prompt = root / 'experiments/prompts/tool_recovery_v1.md'
            prompt.parent.mkdir(parents=True);prompt.write_text('fixed prompt')
            fixed_sha = hashlib.sha256(prompt.read_bytes()).hexdigest()
            for ident, layer in [('combined_control_v1', 'control'), ('combined_prompt_v1', 'prompt')]:
                folder = root / 'runs' / ident;folder.mkdir(parents=True)
                (folder / 'manifest.json').write_text(json.dumps({'experiment': {'id': ident}, 'model_key': '12b',
                    'status': 'local_pass', 'workflow_sha256': 'fixed', 'prompt_sha256': fixed_sha if layer == 'control' else 'candidate',
                    'config': {'ablation': {'layer': layer}, 'serving': {}},
                    'workflow': {'progress_revision': 2, 'system_prompt': '/prompt/' + layer},
                    'solve_elapsed_seconds': 10 if layer == 'control' else 8,
                    'agent': {'submission_origin': 'model'}}))
                (folder / 'evaluation.json').write_text(json.dumps({'exit_code': 0, 'output': 'test_a ... ok\nRan 1 test\nOK'}))
            data = generate(root, spec_key='combined_comparison', report_name='two-model-combined',
                            baseline_id='combined_control_v1', labels={'combined_control_v1': 'control', 'combined_prompt_v1': 'combined'})
            self.assertEqual(data['warnings'], [])
            self.assertIn('-2.0s', data['assessments'][0]['finding'])
            self.assertTrue((root / 'reports/two-model-combined.json').exists())


if __name__ == '__main__':
    unittest.main()
