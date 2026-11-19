import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gemma_lab.config import Project, load
from gemma_lab.prompts import feedback, parse_proposal
from gemma_lab.worker import advance, tick

ROOT = Path(__file__).resolve().parents[1]

class PromptAndWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = Project(self.root, load(ROOT / 'configs/project.toml').raw)

    def test_optimizer_feedback_never_reads_evaluator_or_reference_patch(self):
        run = self.root / 'run'
        run.mkdir()
        (run / 'agent_input.json').write_text(json.dumps({'instance_id': 'x', 'problem_statement': 'fix'}))
        (run / 'manifest.json').write_text(json.dumps({'status': 'local_fail', 'agent': {'reason': 'turn_limit'}}))
        (run / 'evaluation.json').write_text('SECRET EVALUATOR -- not valid JSON')
        (run / 'baseline-evaluation.json').write_text('SECRET BASELINE')
        (run / 'patch.diff').write_text('SECRET REFERENCE')
        (run / 'trajectory.jsonl').write_text(json.dumps({'event': 'tool_result', 'result': {'output': 'PUBLIC'}}) + '\n')
        result = json.dumps(feedback(run))
        self.assertIn('PUBLIC', result)
        self.assertNotIn('SECRET', result)

    def test_invalid_prompt_cannot_overwrite_active_prompt(self):
        with self.assertRaises(ValueError):
            parse_proposal(json.dumps({'system_prompt': 'short', 'rationale': 'x'}))
        valid = {'system_prompt': 'Inspect and reproduce the issue. ' * 5 + 'Call submit_patch to finish.', 'rationale': 'Reduce wasted turns.'}
        self.assertEqual(parse_proposal(json.dumps(valid)), valid)

    def test_failed_trial_is_recorded_before_next_model(self):
        run = self.root / 'run'
        run.mkdir()
        (run / 'manifest.json').write_text(json.dumps({'elapsed_seconds': 2, 'agent': {'reason': 'turn_limit'}}))
        state = {'phase': 'evaluate_prompt', 'model_index': 0, 'prompt_trials': 1,
                 'active_prompt': 'original.md', 'candidate_prompt': 'candidate.md', 'results': []}
        with patch('gemma_lab.worker.start_model'), patch('gemma_lab.worker.demo', return_value=(run, 'incomplete')):
            tick(self.project, state)
        self.assertEqual(state['phase'], 'provision')
        self.assertEqual(state['model_index'], 1)
        self.assertEqual(state['active_prompt'], 'original.md')
        self.assertEqual(state['results'][0]['status'], 'incomplete')

    def test_successful_candidate_becomes_next_trial_prompt(self):
        run = self.root / 'run'
        run.mkdir()
        (run / 'manifest.json').write_text('{}')
        state = {'phase': 'evaluate_prompt', 'model_index': 0, 'prompt_trials': 1,
                 'active_prompt': 'original.md', 'candidate_prompt': 'candidate.md', 'results': []}
        with patch('gemma_lab.worker.start_model'), patch('gemma_lab.worker.demo', return_value=(run, 'local_pass')):
            tick(self.project, state)
        self.assertEqual(state['active_prompt'], 'candidate.md')

    def test_pipeline_finishes_after_largest_model(self):
        state = {'model_index': 2, 'prompt_trials': 1, 'candidate_prompt': 'candidate.md'}
        advance(state, ['e4b', '12b', '31b'])
        self.assertEqual(state['phase'], 'complete')
        self.assertNotIn('candidate_prompt', state)

if __name__ == '__main__':
    unittest.main()
