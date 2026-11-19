"""Passive live observations; never changes model messages or budgets."""
from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from reading_metrics import read
from reading_watch import inspect_log
from staged_report import generate


def main():
    base=ROOT/'runs/staged-v1';base.mkdir(parents=True,exist_ok=True);state=read(base/'state.json');job=state.get('current') or {}
    value={'time':datetime.now(timezone.utc).isoformat(),'status':state.get('status'),'phase':state.get('phase'),'current':job,'waiting_for':state.get('waiting_for'),'alerts':[]}
    if state.get('in_progress') and all(k in job for k in ['model','arm','task']):
        folder=base/job['model']/job['arm']/job['task'];logs=sorted((folder/'logs').glob('*.log'))
        if logs:
            text=logs[0].read_text(errors='replace');value.update(inspect_log(text))
            value['quiet_seconds']=round(datetime.now(timezone.utc).timestamp()-logs[0].stat().st_mtime,1)
            value['observed_denial_mentions']={key:text.count(key) for key in ['inspection_budget_exhausted','duplicate_inspection','test_budget_exhausted']}
            if value['quiet_seconds']>300:value['alerts'].append('Log quiet >300s; inspect server health, not an automatic fail.')
    if state.get('error'):value['alerts'].append(state['error'])
    tmp=base/'live.json.tmp';tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');tmp.replace(base/'live.json')
    with (base/'observations.jsonl').open('a') as output:output.write(json.dumps(value,ensure_ascii=False)+'\n')
    generate(ROOT)
    if state.get('status') in ['complete','needs_review']:subprocess.run(['systemctl','stop','gemma-lab-staged-watch.timer'],check=False)

if __name__=='__main__':main()
