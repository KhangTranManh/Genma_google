"""One measured action per trigger; diagnostics first, then paired real tasks."""
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start
from reading_metrics import read
from simple_report import generate
BASE=ROOT/'runs/simple-v1'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def jobs(plan):
    micro=[{'phase':'micro','model':model,'case':case} for model in plan['models'] for case in plan['micro_cases']]
    real=[{'phase':'real','model':model,'task':task,'arm':arm} for model in plan['models'] for task in plan['tasks'] for arm in plan['arms']]
    return micro+real


def freeze():
    files=list((ROOT/'scripts/simple').glob('*.py'))+list((ROOT/'submission_candidates/simple_v1').rglob('*'))
    files += [ROOT/'configs/simple-study.toml',ROOT/'configs/reading-runtime-v2.toml',ROOT/'configs/project.toml',ROOT/'configs/official-host-requirements.lock']
    files += [ROOT/'scripts/official/reading_metrics.py',ROOT/'scripts/official/start_reading_model_v2.py',ROOT/'data/freshswe/pilot-tasks.jsonl',ROOT/'data/freshswe/sandbox/setup.py']
    files += list((ROOT/'data/freshswe/locks').glob('*.txt'))+list((ROOT/'data/freshswe/snapshots').glob('*.tgz'))
    entries={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    return {'files':entries,'sha256':hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()}


def tick(state,plan):
    for name in ['staged-v1','reading-v2']:
        if read(ROOT/'runs'/name/'state.json').get('status')!='complete':raise RuntimeError('Prior study not complete: '+name)
    frozen=freeze()
    if 'frozen_sha256' not in state:state['frozen_sha256']=frozen['sha256'];save(BASE/'frozen-inputs.json',frozen)
    if state['frozen_sha256']!=frozen['sha256']:raise RuntimeError('Frozen input changed; use a new experiment version')
    images={task:subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','gemma-official-pilot:'+task],text=True).strip() for task in plan['tasks']}
    if state.setdefault('image_ids',images)!=images:raise RuntimeError('Container image changed')
    for job in jobs(plan):
        folder=(BASE/'micro'/job['model']/job['case']) if job['phase']=='micro' else (BASE/'real'/job['model']/job['arm']/job['task'])
        if (folder/'summary.json').exists():continue
        if folder.exists():raise RuntimeError('Incomplete run needs inspection: '+str(folder))
        state.update(current=job,phase='provision');save(BASE/'state.json',state);start(job['model'])
        folder.mkdir(parents=True);state['phase']=job['phase'];save(BASE/'state.json',state)
        if job['phase']=='micro':
            command=[str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/simple/micro_task.py'),'--model',job['model'],'--case',job['case'],'--output',str(folder)];timeout=360
        else:
            command=[str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/simple/run_real_task.py'),'--runtime-version','v2','--phase','agent','--model',job['model'],'--task',job['task'],'--output',str(folder),'--submission-dir',str(ROOT/'submission_candidates/simple_v1'/job['arm']/job['model']),'--experiment','simple-direct-v1','--arm',job['arm']];timeout=1500
        with (folder/'process.log').open('w') as output:subprocess.run(command,check=True,stdout=output,stderr=subprocess.STDOUT,timeout=timeout)
        record=read(folder/'summary.json')
        if not record:raise RuntimeError('Missing measured result')
        error=record.get('error_message') or record.get('error') or ''
        if any(s.lower() in error.lower() for s in ['ContextWindowExceeded','maximum context length','connection refused','AuthenticationError','ModelNotFound']):raise RuntimeError(error)
        state.setdefault('completed',[]).append(dict(job,passed=record.get('diagnostic_pass',record.get('resolved',False))));state['phase']='between_jobs';return
    state.update(status='complete',phase='complete')


def main():
    BASE.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        state=read(BASE/'state.json') or {'status':'running','phase':'queued','experiment':'simple-direct-v1','completed':[]}
        if state.get('status') not in ['complete','needs_review']:
            if state.get('in_progress'):state.update(status='needs_review',error='Previous action interrupted')
            else:
                state['in_progress']=True;save(BASE/'state.json',state)
                try:tick(state,tomllib.loads((ROOT/'configs/simple-study.toml').read_text()))
                except Exception as e:state.update(status='needs_review',error=str(e))
                finally:state['in_progress']=False
            state['updated_at']=datetime.now(timezone.utc).isoformat();save(BASE/'state.json',state)
        generate(ROOT)
        if state.get('status') in ['complete','needs_review']:subprocess.run(['systemctl','stop','gemma-lab-simple.timer'],check=False)
        print(json.dumps(state),flush=True)

if __name__=='__main__':main()
