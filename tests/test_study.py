import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import study_report
import study_runner

class StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'configs').mkdir()
        source_plan = '\n[[stages]]'.join((ROOT / 'configs/study.toml').read_text().split('\n[[stages]]')[:4])
        plan = source_plan.replace('id = "workflow_code_12b_v2"', 'id = "workflow_code_12b_v1"').replace('mode = "workflow_experiment"', 'mode = "definition"').replace('03-workflow-code-v2.md', '03-workflow-code.md')
        (self.root / 'configs/study.toml').write_text(plan)

    def save(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    def test_report_separates_methods_and_keeps_workflow_definition_unexecuted(self):
        for name, method, model in [('a', 'model_sweep_v1', 'e4b'), ('b', 'prompt_only_12b_v2', '12b')]:
            self.save(f'runs/{name}/manifest.json', {'status': 'local_pass', 'model_key': model,
                'agent': {'turns': 3, 'usage': {'completion_tokens': 20}}, 'elapsed_seconds': 2,
                'workflow_sha256': 'fixed', 'prompt_sha256': name, 'experiment': {'id': method}})
        self.save('runs/a/evaluation.json', {'exit_code': 0, 'output': 'test_x ... ok\nRan 1 test in 0.1s\nOK'})
        report = study_report.generate(self.root)
        self.assertEqual([r['run_id'] for r in report['stages'][0]['runs']], ['a'])
        self.assertEqual([r['run_id'] for r in report['stages'][1]['runs']], ['b'])
        self.assertEqual(report['stages'][2]['status'], 'definition_only')
        self.assertEqual(report['stages'][0]['runs'][0]['evaluation']['passed'], 1)
        self.assertIn('Chưa thực thi', (self.root / 'reports/study-report.md').read_text())

    def test_coordinator_cannot_switch_profile_while_worker_is_running(self):
        state = {'status': 'running', 'stage_index': 1}
        with patch.object(study_runner, 'worker_busy', return_value=True), patch.object(study_runner, 'activate') as activate:
            study_runner.tick(self.root, state)
        activate.assert_not_called()
        self.assertEqual(state['status'], 'waiting_for_worker')

    def test_completed_model_sweep_advances_without_mixing_its_runs(self):
        self.save('runs/pipeline/model_sweep_v1/state.json', {'phase': 'complete', 'results': [{'model': 'e4b'}]})
        state = {'status': 'running', 'stage_index': 0}
        with patch.object(study_runner, 'worker_busy', return_value=False), patch.object(study_runner, 'activate') as activate:
            study_runner.tick(self.root, state)
        self.assertEqual(state['stage_index'], 1)
        self.assertEqual(state['completed_stages'], ['model_sweep_v1'])
        activate.assert_not_called()

    def test_infrastructure_error_stops_study_for_review(self):
        self.save('runs/pipeline/model_sweep_v1/state.json', {'phase': 'needs_review', 'error': 'OOM'})
        state = {'stage_index': 0}
        with patch.object(study_runner, 'activate') as activate:
            study_runner.tick(self.root, state)
        self.assertEqual(state['status'], 'needs_review')
        self.assertEqual(state['error'], 'OOM')
        activate.assert_not_called()

    def test_definition_stage_never_executes_workflow_code(self):
        folder = self.root / 'experiments/methods'
        folder.mkdir(parents=True)
        (folder / '03-workflow-code.md').write_text('Definition only')
        state = {'status': 'running', 'stage_index': 2}
        with patch.object(study_runner, 'activate') as activate:
            study_runner.tick(self.root, state)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['definitions']['workflow_code_12b_v1']['status'], 'defined_not_executed')
        activate.assert_not_called()

    def test_completed_metrics_stage_finishes_the_study_without_new_gpu_jobs(self):
        (self.root / 'configs/study.toml').write_text('name = "test"\n[[stages]]\nid = "metrics"\nmode = "metrics"\nprofile = "performance_metrics"\n')
        self.save('runs/pipeline/metrics/state.json', {'phase': 'complete'})
        state = {'status': 'running', 'stage_index': 0}
        with patch('study_runner.subprocess.run') as launch:
            study_runner.tick(self.root, state)
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['completed_stages'], ['metrics'])
        launch.assert_not_called()

    def test_mixed_prompts_in_model_sweep_are_flagged(self):
        for name in ('one', 'two'):
            self.save(f'runs/{name}/manifest.json', {'status': 'incomplete', 'prompt_sha256': name,
                'workflow_sha256': 'same', 'experiment': {'id': 'model_sweep_v1'}})
        report = study_report.collect(self.root)
        self.assertIn('Model sweep contains different prompts', report['stages'][0]['comparison_violations'])

if __name__ == '__main__':
    unittest.main()
