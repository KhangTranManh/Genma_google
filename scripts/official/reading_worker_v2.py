"""Bounded R0/R1/R2 queue; immutable inputs and one task per trigger."""
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from gemma_lab.config import load
from start_reading_model_v2 import start as start_model_v2
from reading_metrics import analyze,read
BASE=ROOT/'runs/reading-v2'
TIMER='gemma-lab-reading-v2.timer'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.json.tmp');temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');temporary.replace(path)


def plan():return tomllib.loads((ROOT/'configs/reading-study-v2.toml').read_text())


def jobs(spec):
    return [{'model':model,'task':task,'arm':arm} for model in spec['models'] for task in spec['development_tasks'] for arm in spec['execution_arm_order']]


def freeze_inputs(root=ROOT):
    files=[root/'configs/reading-runtime-v2.toml',root/'configs/reading-study-v2.toml',root/'configs/project.toml',root/'configs/official-host-requirements.lock']
    files += [root/'scripts/official'/name for name in ['reading_worker_v2.py','reading_metrics.py','run_task.py','start_reading_model_v2.py']]
    files += [root/'src/gemma_lab'/name for name in ['config.py','provisioning.py','serving.py']]
    files += list((root/'submission_candidates/reading_v1').rglob('*'))
    files += list((root/'third_party/kaggle-public').glob('*.whl'))
    files += [root/'data/freshswe/pilot-tasks.jsonl',root/'data/freshswe/sandbox/setup.py']
    files += list((root/'data/freshswe/locks').glob('*.txt'))+list((root/'data/freshswe/snapshots').glob('*.tgz'))
    entries={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    return {'files':entries,'sha256':hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()}


def tick(state,spec):
    if read(ROOT/'runs/official-pilot/state.json').get('status')!='complete':
        state['waiting_for']='Previous official pilot';return
    for task in spec['development_tasks']:
        if not read(ROOT/'runs/official-pilot/preflight'/task/'summary.json').get('usable'):
            raise RuntimeError('No usable calibration for '+task)
    images={task:subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','gemma-official-pilot:'+task],text=True).strip() for task in spec['development_tasks']}
    if state.setdefault('image_ids',images)!=images:raise RuntimeError('Image changed; create a new experiment version')
    frozen=freeze_inputs()
    if 'frozen_sha256' not in state:
        state['frozen_sha256']=frozen['sha256'];save(BASE/'frozen-inputs.json',frozen)
    if state['frozen_sha256']!=frozen['sha256']:raise RuntimeError('Frozen experiment input changed; create a new version')
    for job in jobs(spec):
        folder=BASE/job['model']/job['arm']/job['task']
        if (folder/'summary.json').exists():continue
        if folder.exists():raise RuntimeError('Incomplete task folder requires inspection: '+str(folder))
        state.update(current=job,phase='provision',updated_at=datetime.now(timezone.utc).isoformat());save(BASE/'state.json',state)
        start_model_v2(job['model'])
        folder.mkdir(parents=True)
        state.update(phase='agent',job_started_at=datetime.now(timezone.utc).isoformat());save(BASE/'state.json',state)
        with (folder/'process.log').open('w') as output:
            subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/official/run_task.py'),
                '--runtime-version','v2','--phase','agent','--model',job['model'],'--task',job['task'],'--output',str(folder),
                '--submission-dir',str(ROOT/'submission_candidates/reading_v1'/job['arm']/job['model']),
                '--experiment','focused-reading-v2','--arm',job['arm']],check=True,stdout=output,stderr=subprocess.STDOUT,timeout=1500)
        result=read(folder/'summary.json');metrics=analyze(folder);save(folder/'reading-metrics.json',metrics)
        if not result:raise RuntimeError('Missing evaluator result: '+str(folder))
        error=result.get('error_message') or result.get('error') or ''
        if any(marker.lower() in error.lower() for marker in ['connection refused','ContextWindowExceeded','maximum context length','AuthenticationError','ModelNotFound','No module named']):
            raise RuntimeError('Runtime error needs inspection: '+error)
        state.setdefault('completed',[]).append(dict(job,resolved=bool(result.get('resolved')),autonomous_pass=bool(result.get('resolved') and metrics.get('explicit_nonempty_submission'))))
        state.update(phase='between_jobs',updated_at=datetime.now(timezone.utc).isoformat());return
    state.update(status='complete',phase='complete')


def main():
    BASE.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        state=read(BASE/'state.json') or {'status':'running','phase':'queued','experiment':'focused-reading-v2','official_competition_score':False,'completed':[]}
        if state.get('status') not in ['complete','needs_review']:
            if state.get('in_progress'):
                state.update(status='needs_review',error='Previous job interrupted; inspect before resuming')
            else:
                state['in_progress']=True;save(BASE/'state.json',state)
                try:tick(state,plan())
                except Exception as error:state.update(status='needs_review',error=str(error))
                finally:state['in_progress']=False
            state['updated_at']=datetime.now(timezone.utc).isoformat();save(BASE/'state.json',state)
        subprocess.run([sys.executable,str(ROOT/'scripts/official/reading_report.py'),'--version','v2'],check=False)
        if state.get('status') in ['complete','needs_review']:
            subprocess.run(['systemctl','stop',TIMER],check=False)
        print(json.dumps(state),flush=True)


if __name__=='__main__':main()
