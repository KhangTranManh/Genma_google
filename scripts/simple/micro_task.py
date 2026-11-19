"""Real model + organizer ADK/tools on known fixtures; independent Docker grading."""
import argparse
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP','True')
os.environ.setdefault('LITELLM_TELEMETRY','False')
os.environ.setdefault('OTEL_SDK_DISABLED','true')
ROOT=Path(__file__).resolve().parents[2]
from adk_submission import compile_submission,ModelRegistry
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig
from google.genai import types
from swegemma.config import build_submission_limits
from swegemma.context import SwegemmaContext
from swegemma.sandbox import ContainerConfig,ContainerManager
from swegemma.harness.agent_runner import ToolErrorPlugin

FIXTURES={
 'edit_existing':{
  'files':{'calculator.py':'def increment(value):\n    return value - 1\n',
           'tests/test_calculator.py':'from calculator import increment\ndef test_increment():\n    assert increment(4) == 5\n'},
  'issue':'Fix increment(value) in calculator.py so it adds one for every integer. Use read_file to inspect calculator.py and tests/test_calculator.py, edit_file to fix the existing source, run_command to run pytest, then submit_patch.',
  'grade':'from calculator import increment\nassert [increment(x) for x in [-100,-1,0,4,100]] == [-99,0,1,5,101]\nprint("INDEPENDENT_PASS")\n',
  'required':['read_file','edit_file','run_command','submit_patch']},
 'create_file':{
  'files':{'README.md':'Create the missing message.py module described in the issue.\n',
           'tests/test_message.py':'from message import hello\ndef test_hello():\n    assert hello("Ada") == "Hello, Ada!"\n'},
  'issue':'Create message.py with hello(name), returning "Hello, " followed by name and "!". Use read_file to inspect README.md and tests/test_message.py, write_file with filepath and content to create the module, run_command to run pytest, then submit_patch.',
  'grade':'from message import hello\nassert [hello(x) for x in ["Ada","","a b","Việt"]] == ["Hello, Ada!","Hello, !","Hello, a b!","Hello, Việt!"]\nprint("INDEPENDENT_PASS")\n',
  'required':['read_file','write_file','run_command','submit_patch']}}


def write_fixture(manager,cid,fixture):
    sandbox=manager.get_sandbox(cid)
    sandbox.write_file('.gitignore','__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\n')
    for name,text in fixture['files'].items():
        manager.exec(cid,'mkdir -p /workspace/tests')
        sandbox.write_file(name,text)
    manager.exec(cid,'git init -q && git add -A && git commit -qm baseline')
    return sandbox


async def run(args):
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    fixture=FIXTURES[args.case]
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    started=time.monotonic();counts=Counter();successes=Counter();errors=0;reason=None;patch='';ctx=None;grader_pass=False;required=False;observations=[]
    try:
        cid=manager.start();write_fixture(manager,cid,fixture)
        ctx=SwegemmaContext(docker_manager=manager,container_id=cid,problem_statement=fixture['issue'],repo='diagnostic/fixture',max_tool_calls=24,max_time_minutes=4)
        alias=f'gemma-4-{args.model}-it-qat-w4a16-ct';registry=ModelRegistry();registry.register(alias,LiteLlm(model='openai/'+alias,api_base='http://127.0.0.1:8000/v1',api_key='EMPTY'))
        limits,constraints=build_submission_limits()
        agent=compile_submission(ROOT/'submission_candidates/simple_v1/simple'/args.model,tool_registry=ctx.create_tools(),model_registry=registry,limits=limits,generation_constraints=constraints)
        sessions=InMemorySessionService();session=await sessions.create_session(app_name='simple_micro',user_id='local')
        runner=Runner(agent=agent,app_name='simple_micro',session_service=sessions,plugins=[ToolErrorPlugin()])
        async def solve():
            nonlocal errors
            stream=runner.run_async(user_id='local',session_id=session.id,new_message=types.Content(role='user',parts=[types.Part(text=fixture['issue']+'\nRepository: /workspace. Offline dependencies are already installed. Verification command: PYTHONPATH=/workspace python -m pytest tests -q.')]),run_config=RunConfig(max_llm_calls=16))
            try:
                with (output/'events.jsonl').open('w') as log:
                    async for event in stream:
                        log.write(event.model_dump_json()+'\n');log.flush()
                        for call in event.get_function_calls() or []:
                            counts[call.name]+=1;observations.append({'type':'call','name':call.name,'args':call.args});print('CALL',call.name,json.dumps(call.args,ensure_ascii=False)[:200],flush=True)
                        for response in event.get_function_responses() or []:
                            value=response.response or {};bad=bool(value.get('error') or value.get('error_message') or value.get('status')=='error');errors+=bad
                            successes[response.name]+=not bad
                            observations.append({'type':'response','name':response.name,'error':bad,'value':value});print('RESPONSE',response.name,'error',bad,flush=True)
                        if ctx.patch_submitted:break
            finally:await stream.aclose()
        try:await asyncio.wait_for(solve(),timeout=240)
        except Exception as ex:reason=type(ex).__name__+': '+str(ex)
        patch=ctx.submitted_patch or ''
        (output/'agent.patch').write_text(patch)
        if patch:
            clean=manager.start();sandbox=write_fixture(manager,clean,fixture)
            sandbox.write_file('agent_candidate.diff',patch)
            applied=manager.exec(clean,'git apply agent_candidate.diff')
            if applied.exit_code==0:
                # Run the public tests again in a clean container and a separate known-value grader.
                public=manager.exec(clean,'PYTHONPATH=/workspace python -m pytest tests -q')
                (output/'public-clean.txt').write_text(public.stdout+'\n'+public.stderr)
                sandbox.write_file('_independent_check.py',fixture['grade'])
                check=manager.exec(clean,'PYTHONPATH=/workspace python _independent_check.py')
                grader_pass=public.exit_code==0 and check.exit_code==0 and 'INDEPENDENT_PASS' in check.stdout
                (output/'grader.txt').write_text(check.stdout+'\n'+check.stderr)
        required=all(successes[name]>0 for name in fixture['required'])
        result={'model':args.model,'case':args.case,'scope':'synthetic tool diagnostic, not a real repo score',
                'explicit_submit':bool(ctx and ctx.patch_submitted),'patch_bytes':len(patch.encode()),'independent_pass':grader_pass,
                'required_tools_exercised':required,'diagnostic_pass':bool(grader_pass and required and ctx.patch_submitted),
                'tool_requests':dict(counts),'successful_tool_responses':dict(successes),'tool_errors':errors,'seconds':round(time.monotonic()-started,3),'error':reason,
                'observations':observations,'source':'parsed ADK tool calls; not raw unparsed model tokens'}
        (output/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='observations'},ensure_ascii=False),flush=True)
    finally:manager.cleanup_all()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['12b','31b'],required=True)
    parser.add_argument('--case',choices=list(FIXTURES),required=True);parser.add_argument('--output',required=True)
    asyncio.run(run(parser.parse_args()))
