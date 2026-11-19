"""Passive progress snapshots; no feedback injected into model tasks."""
from datetime import datetime,timezone
from pathlib import Path
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from reading_metrics import read
from reading_watch import inspect_log
from simple_report import generate


def main():
    base=ROOT/'runs/simple-v1';base.mkdir(parents=True,exist_ok=True);state=read(base/'state.json');job=state.get('current') or {}
    value={'time':datetime.now(timezone.utc).isoformat(),'status':state.get('status'),'phase':state.get('phase'),'current':job,'alerts':[]}
    if state.get('in_progress') and job:
        folder=base/'micro'/job['model']/job['case'] if job.get('phase')=='micro' else base/'real'/job['model']/job['arm']/job['task']
        if job.get('phase')=='real':
            logs=sorted((folder/'logs').glob('*.log'))
            if logs:value.update(inspect_log(logs[0].read_text(errors='replace')))
        else:
            path=folder/'process.log'
            if path.exists():value['recent_events']=path.read_text(errors='replace').splitlines()[-6:]
    if state.get('error'):value['alerts'].append(state['error'])
    tmp=base/'live.json.tmp';tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');tmp.replace(base/'live.json')
    generate(ROOT)
    if state.get('status') in ['complete','needs_review']:subprocess.run(['systemctl','stop','gemma-lab-simple-watch.timer'],check=False)

if __name__=='__main__':main()
