"""Organizer compiler validation for flat and staged candidate trees."""
from pathlib import Path
import json
import hashlib
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from adk_submission import compile_submission,validate_directory,ModelRegistry
from google.adk.models.lite_llm import LiteLlm
from adk_eval_core.sandbox.base import AdkSandboxCodeExecutor
from swegemma.config import build_submission_limits
from swegemma.context import SwegemmaContext


def validate(folder,model,arm):
    limits,constraints=build_submission_limits();validate_directory(folder,limits=limits)
    alias=f'gemma-4-{model}-it-qat-w4a16-ct';registry=ModelRegistry()
    registry.register(alias,LiteLlm(model='openai/'+alias,api_base='http://127.0.0.1:8000/v1',api_key='EMPTY'))
    # No execution here; the official evaluator supplies a real sandbox executor at run time.
    executor=AdkSandboxCodeExecutor(sandbox=None)
    agent=compile_submission(folder,tool_registry=SwegemmaContext().create_tools(),model_registry=registry,
                             limits=limits,generation_constraints=constraints,code_executor=executor)
    def tree(node):
        return {'name':node.name,'class':type(node).__name__,'model':str(getattr(getattr(node,'model',None),'model','')),
                'tools':[getattr(tool,'__name__',type(tool).__name__) for tool in getattr(node,'tools',[])],
                'max_iterations':getattr(node,'max_iterations',None),'children':[tree(c) for c in node.sub_agents]}
    result={'compiled':True,'model':model,'arm':arm,'tree':tree(agent),'official_score':False}
    output=ROOT/'reports/staged-v1'/arm;output.mkdir(parents=True,exist_ok=True)
    archive=ROOT/'dist/staged-v1'/arm/model/'submission.zip';archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_symlink():raise ValueError('No symlinks')
            if p.is_file():z.write(p,p.relative_to(folder))
    result['archive']=str(archive.relative_to(ROOT));result['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/f'{model}-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    for model in ['31b','12b']:
        for arm in ['flat','staged']:
            result=validate(ROOT/'submission_candidates/staged_v1'/arm/model,model,arm)
            print(model,arm,'compiled',result['tree']['class'])
