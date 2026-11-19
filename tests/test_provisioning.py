from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch, call
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.config import load
from gemma_lab.provisioning import start_model

ROOT = Path(__file__).resolve().parents[1]

class ProvisioningTests(unittest.TestCase):
    def test_single_model_profile_stops_previous_model_outside_its_order(self):
        project = load(ROOT / 'configs/experiments/prompt_only_v2.toml')
        self.assertEqual(project.raw['automation']['model_order'], ['12b'])
        with patch('gemma_lab.provisioning.health', side_effect=[ValueError('serving 31b'), {}]), \
             patch('gemma_lab.provisioning.stop_manual_server'), \
             patch('gemma_lab.provisioning.subprocess.run', return_value=Mock(stdout='', returncode=0)) as run:
            start_model(project, '12b', project.select('model', '12b')[1])
        calls = run.call_args_list
        old = call(['systemctl', 'stop', 'gemma-lab-vllm@31b.service'], check=True)
        new = call(['systemctl', 'start', 'gemma-lab-vllm@12b.service'], check=True)
        self.assertIn(old, calls)
        self.assertLess(calls.index(old), calls.index(new))

if __name__ == '__main__':
    unittest.main()
