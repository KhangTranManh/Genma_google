"""Opt-in checks against the organizer compiler, separate from the main vLLM env."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/official'))

@unittest.skipUnless(os.environ.get('OFFICIAL_INTEGRATION_TESTS')=='1','run in .venv-official')
class OfficialBridgeTests(unittest.TestCase):
    def test_both_candidates_compile_with_organizer_tool_registry(self):
        from validate_candidate import validate
        for model in ['12b','31b']:
            record=validate(ROOT/'submission_candidates'/model,model)
            self.assertTrue(record['agent_compiled'])
            self.assertFalse(record['official_tasks_scored'])
            self.assertFalse(record['local_python_harness_exported'])

    def test_agent_prompt_excludes_solution_and_verification_patch(self):
        from swegemma.harness.agent_runner import build_agent_prompt
        from swegemma.models import Task
        task=Task(instance_id='fixture',repo='org/repo',base_commit='a'*40,
                  problem_statement='PUBLIC_ISSUE',patch='PRIVATE_SOLUTION_SENTINEL',test_patch='PRIVATE_TEST_SENTINEL')
        import inspect
        signature=inspect.signature(build_agent_prompt)
        # Use the public task prompt helper with its documented budget argument.
        from swegemma.context import SwegemmaContext
        context=SwegemmaContext(task=task,max_time_minutes=15,max_tool_calls=96)
        kwargs={}
        for name,p in signature.parameters.items():
            if name=='task':kwargs[name]=task
            elif name in ('context','ctx'):kwargs[name]=context
            elif name=='config':
                from swegemma.config import EvalConfig
                from adk_submission import ModelRegistry
                kwargs[name]=EvalConfig(tasks_path=ROOT/'data/freshswe/pilot-tasks.jsonl',snapshots_dir=ROOT/'data/freshswe/snapshots',results_dir=ROOT/'runs/official-test-fixture',submission_dir=ROOT/'submission_candidates/12b',models=ModelRegistry())
            elif p.default is inspect.Parameter.empty:raise AssertionError('Inspect new required argument: '+name)
        prompt=build_agent_prompt(**kwargs)
        self.assertIn('PUBLIC_ISSUE',prompt)
        self.assertNotIn('PRIVATE_SOLUTION_SENTINEL',prompt)
        self.assertNotIn('PRIVATE_TEST_SENTINEL',prompt)

    def test_reports_never_count_pending_runs_as_pass(self):
        import report
        with tempfile.TemporaryDirectory() as directory:
            result=report.generate(Path(directory))
            self.assertEqual(len(result['rows']),6)
            self.assertTrue(all(r['status']=='pending' for r in result['rows']))

if __name__=='__main__':unittest.main()
