"""Validate/compile a submission folder with the organizer libraries (any root agent class)."""
import os,sys,json
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP','True');os.environ.setdefault('OTEL_SDK_DISABLED','true')
from pathlib import Path
from adk_submission import compile_submission,validate_directory,ModelRegistry,discover_adapters
from google.adk.models.lite_llm import LiteLlm
from swegemma.config import build_submission_limits
from swegemma.context import SwegemmaContext
folder=Path(sys.argv[1]).resolve();limits,constraints=build_submission_limits();validate_directory(folder,limits=limits)
reg=ModelRegistry()
for m in ['31b','12b']:a=f'gemma-4-{m}-it-qat-w4a16-ct';reg.register(a,LiteLlm(model='openai/'+a,api_base='http://127.0.0.1:8000/v1',api_key='EMPTY'))
agent=compile_submission(folder,tool_registry=SwegemmaContext(max_tool_calls=96,max_time_minutes=15).create_tools(),model_registry=reg,limits=limits,generation_constraints=constraints,adapter_manifest=discover_adapters(str(folder)))
def walk(a,d=0):
    print('  '*d+f"{type(a).__name__}:{a.name}"+(f" tools={[getattr(t,'__name__',type(t).__name__) for t in getattr(a,'tools',[])]}" if getattr(a,'tools',None) else ''))
    for s in getattr(a,'sub_agents',[]) or []:walk(s,d+1)
walk(agent);print('COMPILED OK')
