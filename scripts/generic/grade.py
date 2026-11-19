"""Official-style hidden grade for any FreshSWE task with a built image (run with .venv-official).

Uses swegemma.harness.verification.verify_task: the dataset's FAIL_TO_PASS / PASS_TO_PASS tests in a clean container.
  --preflight : baseline (empty patch) must be unresolved and gold patch resolved.
  --patch F   : grade a candidate patch (git diff text).
"""
import argparse,asyncio,json,os,time
from pathlib import Path
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP','True');os.environ.setdefault('OPENAI_API_KEY','EMPTY');os.environ.setdefault('OTEL_SDK_DISABLED','true')
from adk_submission import ModelRegistry
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.models import load_tasks
from swegemma.harness.verification import verify_task
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/freshswe'


def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str)+'\n')


async def grade(tid,patch,out):
    task=next(t for t in load_tasks(DATA/'tasks.jsonl') if t.instance_id==tid)
    config=EvalConfig(tasks_path=DATA/'tasks.jsonl',snapshots_dir=DATA/'snapshots',results_dir=out,submission_dir=ROOT/'submission_candidates/31b',models=ModelRegistry(),
                      image='gemma-official-pilot:'+tid.lower(),sandbox='docker',timeout_seconds=60,verification_timeout_seconds=300,display_mode='quiet',verbose=False)
    ev=Evaluator(config);t=time.perf_counter()
    r=await verify_task(ev.docker,config,task,DATA/'snapshots'/f'{tid}.tgz',agent_patch=patch,start_time=t)
    return {'resolved':r.resolved,'exit_code':r.test_exit_code,'error':r.error,'seconds':round(time.perf_counter()-t,1)},r.test_output


def main():
    p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--out',required=True);p.add_argument('--preflight',action='store_true');p.add_argument('--patch');a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if a.preflight:
        task=next(t for t in load_tasks(DATA/'tasks.jsonl') if t.instance_id==a.task)
        base,bo=asyncio.run(grade(a.task,'',out));gold,go=asyncio.run(grade(a.task,task.patch,out))
        (out/'baseline-output.txt').write_text(bo);(out/'gold-output.txt').write_text(go)
        r={'task':a.task,'baseline':base,'gold':gold,'usable':(not base['resolved']) and gold['resolved']}
    else:
        res,o=asyncio.run(grade(a.task,Path(a.patch).read_text(),out));(out/'test-output.txt').write_text(o);r=dict(task=a.task,**res)
    dump(out/'grade.json',r);print(json.dumps(r))

if __name__=='__main__':main()
