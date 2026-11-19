import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.config import Project, load
from gemma_lab.runs import execute, expand, prepare
from gemma_lab.serving import serve_command
from gemma_lab.submission import package
from gemma_lab.tasks import agent_input, read_tasks

ROOT = Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original = load(ROOT / 'configs/project.toml')
        self.project = Project(self.root, original.raw)
        self.key, self.model = self.project.select('model')
        self.task = dict(instance_id='requests-1', repo='psf/requests', base_commit='abc',
                         problem_statement='Fix bug', hints_text='', patch='SECRET',
                         test_patch='SECRET_TEST', evaluator_secret='PRIVATE')

    def test_agent_input_excludes_reference_data(self):
        self.assertEqual(set(agent_input(self.task)),
                         {'instance_id', 'repo', 'base_commit', 'problem_statement', 'hints_text'})
        run = prepare(self.project, self.task, self.key, self.model)
        self.assertNotIn('SECRET', (run / 'agent_input.json').read_text())
        self.assertNotIn('PRIVATE', (run / 'manifest.json').read_text())

    def test_repo_selection_and_duplicate_detection(self):
        path = self.root / 'tasks.jsonl'
        other = dict(self.task, instance_id='rich-1', repo='Textualize/rich')
        path.write_text('\n'.join(json.dumps(t) for t in [self.task, other]))
        self.assertEqual([t['instance_id'] for t in read_tasks(path, 'psf/requests')], ['requests-1'])
        path.write_text('\n'.join(json.dumps(self.task) for _ in range(2)))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            list(read_tasks(path))

    def test_vllm_switches_model_without_shell(self):
        _, model = self.project.select('model', '12b')
        command = serve_command(self.project, model)
        self.assertEqual(command[:2], ['vllm', 'serve'])
        self.assertIn(model['alias'], command)
        self.assertEqual(command[command.index('--tensor-parallel-size') + 1], '2')
        self.assertEqual(expand(['tool', '{submission}'], {'submission': '/a path/$x'}),
                         ['tool', '/a path/$x'])

    def test_archive_is_only_submission_and_requires_validation(self):
        source = self.project.path('submission')
        source.mkdir()
        (source / 'agent.yaml').write_text('official sample placeholder for test\n')
        (source / 'prompts').mkdir()
        (source / 'prompts/system.md').write_text('prompt')
        (self.root / 'host-secret').write_text('private')
        with self.assertRaisesRegex(ValueError, 'validator'):
            package(self.project, [])
        target = package(self.project, [], allow_unvalidated=True)
        self.assertEqual(target.name, 'submission.unvalidated.zip')
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.namelist(), ['agent.yaml', 'prompts/system.md'])
        (source / 'escape').symlink_to(self.root / 'host-secret')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            package(self.project, [], allow_unvalidated=True)

    def test_validator_failure_prevents_archive(self):
        source = self.project.path('submission')
        source.mkdir()
        (source / 'agent.yaml').write_text('sample')
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            package(self.project, [sys.executable, '-c', 'raise SystemExit(1)'])
        self.assertFalse(self.project.path('dist').exists())

    def test_process_success_is_not_a_solved_issue(self):
        run = prepare(self.project, self.task, self.key, self.model)
        self.assertEqual(execute(self.project, [sys.executable, '-c', 'print("done")'], run), 0)
        self.assertEqual(json.loads((run / 'manifest.json').read_text())['status'], 'harness_finished')
        self.assertEqual((run / 'harness.log').read_text().strip(), 'done')

    def test_missing_executable_records_failure(self):
        run = prepare(self.project, self.task, self.key, self.model)
        with self.assertRaises(OSError):
            execute(self.project, ['/nonexistent/gemma-harness'], run)
        self.assertEqual(json.loads((run / 'manifest.json').read_text())['status'], 'failed')

if __name__ == '__main__':
    unittest.main()
