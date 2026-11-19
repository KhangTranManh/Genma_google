import json
from pathlib import Path
import sys
import tempfile
import unittest
import threading
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from comparison_report import generate, protocol
from model_metrics import summarize, sample_gpu

class ComparisonMetricsTests(unittest.TestCase):
    def test_protocol_ignores_queue_identity_but_not_budgets(self):
        base = {'workflow_sha256': 'code', 'prompt_sha256': 'prompt', 'workflow': {'time_limit_seconds': 900},
                'config': {'serving': {'tensor_parallel_size': 2}, 'defaults': {'model': '31b'}}}
        state = {'invariants': {'dataset_sha256': 'data'}}
        other = dict(base, config={'serving': {'tensor_parallel_size': 2}, 'defaults': {'model': 'e4b'}})
        self.assertEqual(protocol(base, state), protocol(other, state))
        changed = dict(base, workflow={'time_limit_seconds': 240})
        self.assertNotEqual(protocol(base, state), protocol(changed, state))

    def test_metrics_summary_uses_medians_and_labels_sampled_memory(self):
        trials = [{'end_to_end_tokens_per_second': value, 'ttft_seconds': value / 100,
                   'approx_decode_tokens_per_second': None} for value in (10, 20, 90)]
        samples = [{'index': 0, 'memory_used_mib': 100}, {'index': 0, 'memory_used_mib': 150},
                   {'index': 1, 'memory_used_mib': 120}]
        result = summarize(trials, samples)
        self.assertEqual(result['median_end_to_end_tokens_per_second'], 20)
        self.assertEqual(result['median_ttft_ms'], 200)
        self.assertEqual(result['sampled_max_memory_mib'], {'0': 150, '1': 120})
        self.assertIsNone(result['median_approx_decode_tokens_per_second'])

    def test_gpu_sampling_failure_is_recorded_instead_of_fabricating_a_measurement(self):
        samples, errors = [], []
        with patch('model_metrics.subprocess.run', return_value=Mock(returncode=1, stderr='driver unavailable')):
            sample_gpu(threading.Event(), samples, 0.5, errors)
        self.assertEqual(samples, [])
        self.assertEqual(errors, ['driver unavailable'])

    def test_missing_evidence_is_not_reported_as_a_pass_or_zero_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'configs').mkdir()
            (root / 'configs/study.toml').write_text('''[comparison]
id = "comparison"
experiments = ["retry", "control"]
models = ["e4b", "12b", "31b"]
metrics = "metrics"
''')
            run = root / 'runs/one'
            run.mkdir(parents=True)
            (run / 'manifest.json').write_text(json.dumps({'status': 'incomplete', 'model_key': '31b',
                'experiment': {'id': 'retry'}, 'workflow_sha256': 'code', 'prompt_sha256': 'prompt',
                'workflow': {'time_limit_seconds': 900}, 'agent': {'reason': 'turn_limit'}}))
            result = generate(root)
            self.assertFalse(result['rows'][0]['submitted'])
            self.assertIsNone(result['rows'][0]['performance'])
            self.assertIsNone(result['rows'][0]['independent_tests_passed'])
            self.assertIn('chờ chạy', (root / 'reports/model-comparison.md').read_text())
            self.assertIn('benchmark_tokens_per_second', (root / 'reports/model-comparison.csv').read_text())

if __name__ == '__main__':
    unittest.main()
