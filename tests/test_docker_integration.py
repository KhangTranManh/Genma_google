"""Opt-in integration test that uses the built image but no GPU/model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.local import evaluate
from gemma_lab.sandbox import DockerSandbox

@unittest.skipUnless(os.environ.get('GEMMA_DOCKER_TESTS') == '1', 'set GEMMA_DOCKER_TESTS=1 for Docker integration')
class DockerIntegrationTests(unittest.TestCase):
    def test_clean_checkout_patch_and_separate_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            (source / 'mathlib.py').write_text('def increment(x):\n    return x - 1\n')
            for command in (['git', 'init', '-q'], ['git', 'add', '.'],
                            ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'baseline']):
                subprocess.run(command, cwd=source, capture_output=True, check=True)
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
            evaluator = Path(directory) / 'check.py'
            evaluator.write_text('from mathlib import increment\nassert increment(2) == 3\nprint("independent check passed")\n')
            settings = {'image': 'gemma-lab-sandbox:local', 'command_timeout_seconds': 10, 'tool_output_chars': 4000}
            with DockerSandbox(settings['image'], 10, 4000) as agent:
                agent.checkout(source, commit)
                config = json.loads(subprocess.check_output(['docker', 'inspect', agent.name]))[0]
                self.assertEqual(config['HostConfig']['NetworkMode'], 'none')
                self.assertTrue(config['HostConfig']['ReadonlyRootfs'])
                self.assertFalse(any(m['Type'] == 'bind' for m in config['Mounts']))
                self.assertEqual(agent.run_command('test ! -e /tmp/check.py')['exit_code'], 0)
                self.assertIn('error', agent.call('write_file', {'filepath': '../escape', 'content': 'bad'}))
                agent.call('edit_file', {'filepath': 'mathlib.py', 'old_string': 'x - 1', 'new_string': 'x + 1'})
                patch = agent.patch()
            baseline = evaluate(settings, source, commit, '', evaluator)
            fixed = evaluate(settings, source, commit, patch, evaluator)
            self.assertNotEqual(baseline['exit_code'], 0)
            self.assertEqual(fixed['exit_code'], 0)
            self.assertEqual((source / 'mathlib.py').read_text(), 'def increment(x):\n    return x - 1\n')

if __name__ == '__main__':
    unittest.main()
