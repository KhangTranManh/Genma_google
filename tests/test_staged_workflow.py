import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bounded_ops',ROOT/'experiments/skills/bounded-workspace/scripts/workspace_ops.py')
ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)

class BoundedOperationsTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        (self.root/'module.py').write_text('\n'.join('line '+str(i) for i in range(200)))
        self.state=self.root/'state.json'
    def call(self,action='read',path='module.py',start=1,end=5,needle=''):
        args=argparse.Namespace(action=action,path=path,start=start,end=end,needle=needle)
        return ops.operate(args,self.root,self.state)
    def test_unchanged_reads_are_denied_after_two_successes(self):
        self.assertEqual(self.call()['status'],'ok');self.assertEqual(self.call()['status'],'ok')
        self.assertEqual(self.call()['reason'],'duplicate_inspection')
        self.assertEqual(self.call('status')['inspection_calls'],2)
    def test_changed_content_can_be_read_within_remaining_total_budget(self):
        self.call();self.call();(self.root/'module.py').write_text('new content')
        self.assertEqual(self.call()['status'],'ok')
    def test_total_inspection_budget_cannot_be_reset_by_changing_ranges(self):
        for i in range(1,9):self.assertEqual(self.call(start=i,end=i)['status'],'ok')
        self.assertEqual(self.call(start=9,end=9)['reason'],'inspection_budget_exhausted')
    def test_traversal_symlinks_and_large_windows_are_rejected(self):
        with self.assertRaises(ValueError):self.call(path='../outside')
        (self.root/'link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):self.call(path='link')
        with self.assertRaises(ValueError):self.call(end=100)
    def test_long_lines_are_truncated(self):
        (self.root/'module.py').write_text('x'*4000)
        result=self.call();self.assertTrue(result['truncated']);self.assertEqual(len(result['content']),2400)

class StagedQueueAndReportTests(unittest.TestCase):
    def test_queue_waits_without_switching_gpu_while_reading_study_runs(self):
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts/workflow'))
        import staged_worker
        state={}
        with patch.object(staged_worker,'read',return_value={'status':'running'}),patch.object(staged_worker,'start_model_v2') as start:
            staged_worker.tick(state,staged_worker.plan())
        start.assert_not_called()
        self.assertIn('Reading v2',state['waiting_for'])
        self.assertEqual(len(staged_worker.jobs(staged_worker.plan())),12)

    def test_script_denials_are_measured_and_not_hidden_by_zero_native_reads(self):
        sys.path.insert(0,str(ROOT/'scripts/workflow'))
        from staged_report import stage_metrics
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'traces').mkdir()
            step={'source':'agent','extra':{'author':'editor'},'tool_calls':[{'function_name':'run_skill_script','arguments':{'args':['read','--path','a.py']}}],
                  'observation':{'content':json.dumps({'status':'success','stdout':json.dumps({'status':'denied','reason':'duplicate_inspection'})})}}
            (folder/'traces/t.json').write_text(json.dumps({'steps':[step]}))
            result=stage_metrics(folder)
            self.assertEqual(result['bounded_inspection_requests'],1)
            self.assertEqual(result['denied_operations'],{'duplicate_inspection':1})
            self.assertEqual(result['phase_sequence'],['editor'])

@unittest.skipUnless(os.environ.get('OFFICIAL_INTEGRATION_TESTS')=='1','run with official ADK environment')
class StagedIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_workflow_runs_two_repair_cycles_and_reaches_submitter(self):
        from adk_submission import compile_submission,ModelRegistry
        from adk_eval_core.sandbox.base import AdkSandboxCodeExecutor
        from google.adk.models.base_llm import BaseLlm
        from google.adk.models.llm_response import LlmResponse
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        from swegemma.context import SwegemmaContext
        from swegemma.config import build_submission_limits
        observed=[]
        class FixtureLlm(BaseLlm):
            async def generate_content_async(self,llm_request,stream=False):
                text=str(llm_request.config.system_instruction)
                if 'You plan a software repair' in text:role='planner'
                elif 'You implement a minimal repair' in text:role='editor'
                elif 'You verify the proposed patch' in text:role='verifier'
                elif 'You finalize the patch' in text:role='submitter'
                else:raise AssertionError('Unknown stage')
                observed.append(role)
                yield LlmResponse(content=types.Content(role='model',parts=[types.Part(text='Fixture stage completed; not a real task result.')]))
        alias='gemma-4-12b-it-qat-w4a16-ct';registry=ModelRegistry();registry.register(alias,FixtureLlm(model=alias))
        limits,constraints=build_submission_limits()
        agent=compile_submission(ROOT/'submission_candidates/staged_v1/staged/12b',tool_registry=SwegemmaContext().create_tools(),model_registry=registry,limits=limits,generation_constraints=constraints,code_executor=AdkSandboxCodeExecutor(sandbox=None))
        self.assertEqual(agent.sub_agents[0].tools,[])
        self.assertEqual(agent.sub_agents[1].max_iterations,2)
        editor,verifier=agent.sub_agents[1].sub_agents
        self.assertNotIn('submit_patch',[getattr(t,'__name__',None) for t in editor.tools])
        self.assertNotIn('write_file',[getattr(t,'__name__',None) for t in verifier.tools])
        sessions=InMemorySessionService();session=await sessions.create_session(app_name='staged_test',user_id='fixture')
        runner=Runner(agent=agent,app_name='staged_test',session_service=sessions)
        async for event in runner.run_async(user_id='fixture',session_id=session.id,new_message=types.Content(role='user',parts=[types.Part(text='Fix a fixture issue.')])):pass
        self.assertEqual(observed,['planner','editor','verifier','editor','verifier','submitter'])

    async def test_skill_wrapper_executes_and_enforces_duplicate_limit_in_docker(self):
        from google.adk.skills import load_skill_from_dir
        from google.adk.tools.skill_toolset import _SkillScriptCodeExecutor
        from google.adk.code_executors.code_execution_utils import CodeExecutionInput
        from adk_eval_core.sandbox.base import AdkSandboxCodeExecutor
        from swegemma.sandbox import ContainerConfig,ContainerManager
        from swegemma.context import SwegemmaContext
        manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
        cid=manager.start()
        try:
            context=SwegemmaContext(docker_manager=manager,container_id=cid)
            context.sandbox.write_file('sample.py','value = 1\n')
            executor=AdkSandboxCodeExecutor(sandbox=context.sandbox,timeout_seconds=10)
            wrapper=_SkillScriptCodeExecutor(executor,10)
            skill=load_skill_from_dir(ROOT/'experiments/skills/bounded-workspace')
            code=wrapper._build_wrapper_code(skill,'scripts/workspace_ops.py',['read','--path','sample.py','--start','1','--end','1'])
            results=[executor.execute_code(None,CodeExecutionInput(code=code)) for _ in range(3)]
            parsed=[json.loads(r.stdout) for r in results]
            self.assertEqual([p['status'] for p in parsed],['ok','ok','denied'])
            self.assertEqual(parsed[-1]['reason'],'duplicate_inspection')
        finally:manager.cleanup_all()

if __name__=='__main__':unittest.main()
