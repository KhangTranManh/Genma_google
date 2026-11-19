import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from progress_report import generate

class ProgressReportTests(unittest.TestCase):
    def test_recovered_patches_and_harness_submissions_are_not_autonomous_submissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'configs').mkdir()
            (root / 'configs/study.toml').write_text('''[progress_comparison]
experiments = ["progress_baseline_v1", "progress_guard_v1", "progress_finish_v1"]
models = ["e4b", "12b", "31b"]
''')
            for name, experiment, reason, origin in [('a', 'progress_baseline_v1', 'turn_limit', None),
                                                     ('c', 'progress_finish_v1', 'harness_submitted', 'harness')]:
                run = root / 'runs' / name
                run.mkdir(parents=True)
                (run / 'manifest.json').write_text(json.dumps({'status': 'incomplete' if name == 'a' else 'local_pass',
                    'experiment': {'id': experiment}, 'model_key': '12b', 'prompt_sha256': 'fixed',
                    'workflow_sha256': 'fixed', 'workflow': {}, 'config': {'serving': {}},
                    'agent': {'reason': reason, 'submission_origin': origin}, 'solve_elapsed_seconds': 1}))
                filename = 'recovered-evaluation.json' if name == 'a' else 'evaluation.json'
                (run / filename).write_text(json.dumps({'exit_code': 0, 'output': 'test_x ... ok\nRan 1 test in 0.0s\nOK'}))
            report = generate(root)
            first, second = report['rows']
            self.assertIsNone(first['submission_origin'])
            self.assertIsNone(first['evaluation'])
            self.assertEqual(first['recovered_evaluation']['exit_code'], 0)
            self.assertEqual(second['submission_origin'], 'harness')
            self.assertEqual(report['warnings'], [])
            text = (root / 'reports/anti-loop-comparison.md').read_text()
            self.assertIn('chỉ chẩn đoán', text)
            self.assertIn('harness', text)

if __name__ == '__main__':
    unittest.main()
