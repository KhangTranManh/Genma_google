"""Run a submission folder through the organizer Evaluator on FreshSWE tasks (agent phase + official grade).
One output folder per task; never overwrites. Runtime v2: 16K context served by the reading-v2 vLLM service.
  .venv-official/bin/python scripts/generic/run_official.py --submission DIR --model 31b --tasks ... --out runs/official-generic-v1
"""
import argparse,asyncio,hashlib,json,os,sys,time
from pathlib import Path
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP','True');os.environ.setdefault('LITELLM_TELEMETRY','False');os.environ.setdefault('OTEL_SDK_DISABLED','true');os.environ.setdefault('OPENAI_API_KEY','EMPTY')
from adk_submission import ModelRegistry
from google.adk.models.lite_llm import LiteLlm
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.models import load_tasks
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/freshswe'
sys.path.insert(0,str(ROOT/'scripts/official'));from start_reading_model_v2 import start


def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str)+'\n')


async def one(task,sub,model,out):
    alias=f'gemma-4-{model}-it-qat-w4a16-ct';reg=ModelRegistry();reg.register(alias,LiteLlm(model='openai/'+alias,api_base='http://127.0.0.1:8000/v1',api_key='EMPTY'))
    cfg=EvalConfig(tasks_path=DATA/'tasks.jsonl',snapshots_dir=DATA/'snapshots',results_dir=out,submission_dir=sub,models=reg,image='gemma-official-pilot:'+task.instance_id.lower(),sandbox='docker',
                   timeout_seconds=60,verification_timeout_seconds=300,max_time_minutes=15,max_tool_calls=96,max_turns=48,graph_dir=str(DATA/'graphs'),embeddings_dir=str(DATA/'embeddings'),
                   events_compaction_config=EventsCompactionConfig(compaction_interval=10,overlap_size=2,token_threshold=4096,event_retention_size=5),display_mode='quiet',verbose=False)
    ev=Evaluator(cfg);t=time.monotonic()
    try:
        r=await ev.evaluate_task(task)
        rec=r.model_dump(exclude={'trace','agent_patch'});rec.update(seconds=round(time.monotonic()-t,1),official_competition_score=False)
        (out/'agent.patch').write_text(r.agent_patch or '');(out/'test-output.txt').write_text(r.test_output or '')
        return rec
    finally:ev.docker.cleanup_all()


def main():
    p=argparse.ArgumentParser();p.add_argument('--submission',required=True);p.add_argument('--model',default='31b');p.add_argument('--tasks',nargs='+',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    sub=Path(a.submission).resolve();base=Path(a.out).resolve();base.mkdir(parents=True,exist_ok=True)
    dump(base/'inputs.json',{'submission':str(sub),'files':{str(q.relative_to(sub)):hashlib.sha256(q.read_bytes()).hexdigest() for q in sub.rglob('*') if q.is_file()},'tasks':a.tasks,'model':a.model})
    tasks={t.instance_id:t for t in load_tasks(DATA/'tasks.jsonl')};start(a.model);summary=[]
    for tid in a.tasks:
        out=base/tid
        if (out/'summary.json').exists():summary.append(json.loads((out/'summary.json').read_text()));continue
        out.mkdir(parents=True,exist_ok=True)
        try:rec=asyncio.run(one(tasks[tid],sub,a.model,out))
        except Exception as e:rec={'instance_id':tid,'resolved':False,'error':repr(e)[:500]}
        dump(out/'summary.json',rec);summary.append(rec);print(tid,rec.get('resolved'),rec.get('error'),flush=True)
        dump(base/'summary.json',{'resolved':sum(1 for r in summary if r.get('resolved')),'n':len(summary),'results':[{k:r.get(k) for k in ['instance_id','resolved','error','seconds','test_exit_code']} for r in summary]})

if __name__=='__main__':main()
