import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.config import Project, load
from gemma_lab.experiments import archive_results, validate_selection
from gemma_lab.worker import state_path, tick
from gemma_lab.prompts import propose

ROOT = Path(__file__).resolve().parents[1]

class ExperimentTests(unittest.TestCase):
    def test_inherited_profiles_preserve_project_root_and_isolate_states(self):
        model = load(ROOT / 'configs/experiments/model_sweep.toml')
        prompt = load(ROOT / 'configs/experiments/prompt_only.toml')
        self.assertEqual(model.root, ROOT)
        self.assertEqual(prompt.root, ROOT)
        self.assertNotEqual(state_path(model), state_path(prompt))
        self.assertEqual(prompt.raw['automation']['model_order'], ['12b'])

    def test_model_sweep_rejects_changed_prompt_and_prompt_method_rejects_model_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / 'prompt.md'
            candidate.write_text('different prompt')
            with self.assertRaisesRegex(ValueError, 'fixes the prompt'):
                validate_selection(load(ROOT / 'configs/experiments/model_sweep.toml'), '12b', candidate)
        with self.assertRaisesRegex(ValueError, 'fixes the model'):
            validate_selection(load(ROOT / 'configs/experiments/prompt_only.toml'), '31b')
        with self.assertRaisesRegex(ValueError, 'definition-only'):
            validate_selection(load(ROOT / 'configs/experiments/workflow_code.toml'), '12b')

    def test_model_sweep_never_enters_prompt_optimization_after_failed_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / 'manifest.json').write_text('{}')
            project = load(ROOT / 'configs/experiments/model_sweep.toml')
            state = {'phase': 'demo', 'model_index': 0, 'active_prompt': 'submission/prompts/system.md', 'results': []}
            with patch('gemma_lab.worker.start_model'), patch('gemma_lab.worker.demo', return_value=(run, 'incomplete')):
                tick(project, state)
            self.assertEqual(state['phase'], 'provision')
            self.assertEqual(state['model_index'], 1)
            self.assertEqual(state['active_prompt'], 'submission/prompts/system.md')

    def test_archive_preserves_failed_runs_and_does_not_relabel_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = Project(root, load(ROOT / 'configs/project.toml').raw)
            run = project.path('runs') / 'old-run'
            run.mkdir(parents=True)
            (run / 'manifest.json').write_text(json.dumps({'status': 'failed', 'error': 'timed out', 'model_key': '31b'}))
            records = archive_results(project)
            self.assertEqual(records[0]['method'], 'legacy_mixed')
            self.assertEqual(records[0]['error'], 'timed out')
            self.assertFalse(records[0]['comparison_valid'])
            archive = root / 'experiments/results/legacy_mixed/old-run/raw.tar.gz'
            before = archive.read_bytes()
            archive_results(project)
            self.assertEqual(archive.read_bytes(), before)

    def test_model_sweep_cannot_generate_prompt_candidates(self):
        project = load(ROOT / 'configs/experiments/model_sweep.toml')
        with patch('gemma_lab.prompts.health') as endpoint:
            with self.assertRaisesRegex(ValueError, 'prompt_only'):
                propose(project, ROOT / 'runs/unused', '12b', project.select('model', '12b')[1])
            endpoint.assert_not_called()

    def test_cyclic_config_extends_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_text('extends = "config.toml"\n')
            with self.assertRaisesRegex(ValueError, 'Cyclic'):
                load(path)

if __name__ == '__main__':
    unittest.main()
