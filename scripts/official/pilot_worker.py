"""One bounded official-runtime pilot action per timer; independent of URLKit studies."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from gemma_lab.config import load
from gemma_lab.provisioning import start_model

STATE = ROOT/'runs/official-pilot/state.json'
TASKS = ['w3lib_264', 'packaging_1125', 'platformdirs_540']
MODELS = ['12b', '31b']


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save(state):
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    STATE.parent.mkdir(parents=True,exist_ok=True)
    tmp=STATE.with_suffix('.json.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(STATE)


def fingerprint():
    files = list((ROOT/'scripts/official').glob('*.py'))
    files += list((ROOT/'submission_candidates').rglob('*'))
    files += [ROOT/'data/freshswe/pilot-tasks.jsonl',ROOT/'data/freshswe/sandbox/setup.py']
    files += list((ROOT/'data/freshswe/locks').glob('*.txt'))
    files += list((ROOT/'data/freshswe/snapshots').glob('*.tgz'))
    files += [ROOT/'configs/project.toml', ROOT/'configs/official-host-requirements.lock']
    entries={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    return hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()


def tick(state):
    old=read(ROOT/'runs/study/state.json')
    if old.get('status') != 'complete':
        state['waiting_for']='URLKit study to finish';return
    if state.get('status') in ['complete','needs_review']:
        return
    state.pop('waiting_for',None)
    image_ids = {task:subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','gemma-official-pilot:'+task],text=True).strip() for task in TASKS}
    if state.setdefault('image_ids',image_ids) != image_ids:
        raise RuntimeError('Pilot container image changed')
    for task in TASKS:
        result=read(ROOT/'runs/official-pilot/preflight'/task/'summary.json')
        if result:
            if not result.get('usable'):
                raise RuntimeError('Environment preflight failed: '+task)
            continue
        build=ROOT/'runs'/f'official-build-{task}.log'
        with build.open('a') as output:
            subprocess.run([sys.executable,str(ROOT/'scripts/official/prepare_pilot.py'),'--task',task],check=True,stdout=output,stderr=subprocess.STDOUT,timeout=1500)
        folder=ROOT/'runs/official-pilot/preflight'/task
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/'process.log').open('a') as output:
            subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/official/run_task.py'),'--phase','preflight','--task',task,'--output',str(folder)],check=True,stdout=output,stderr=subprocess.STDOUT,timeout=1000)
        state['phase']='preflight';state['last_task']=task;return
    jobs=[(model,task) for model in MODELS for task in TASKS]
    for model,task in jobs:
        folder=ROOT/'runs/official-pilot'/model/task
        if (folder/'summary.json').exists():
            continue
        state.update(phase='agent',current_model=model,current_task=task);save(state)
        project=load(ROOT/'configs/project.toml')
        start_model(project,model,project.select('model',model)[1])
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/'process.log').open('a') as output:
            subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/official/run_task.py'),'--phase','agent','--model',model,'--task',task,'--output',str(folder)],check=True,stdout=output,stderr=subprocess.STDOUT,timeout=1500)
        record=read(folder/'summary.json')
        if record.get('error') and not record.get('agent_patch') and not (folder/'agent.patch').read_text().strip():
            raise RuntimeError('Task stopped with error and no patch; inspect '+str(folder/'process.log'))
        state.setdefault('completed',[]).append({'model':model,'task':task,'resolved':record.get('resolved',False)})
        return
    state.update(status='complete',phase='complete')


def main():
    STATE.parent.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        state=read(STATE) or {'status':'running','phase':'preflight','models':MODELS,'tasks':TASKS,'dataset':'FreshSWE-Py independent pilot','official_competition_score':False}
        if state.get('status') in ['complete','needs_review']:
            subprocess.run(['systemctl','stop','gemma-lab-official-pilot.timer'],check=False);return
        if state.get('in_progress'):
            state.update(status='needs_review',error='Previous action interrupted; inspect logs before resuming')
        else:
            try:
                frozen=fingerprint()
                if state.setdefault('frozen_sha256',frozen) != frozen:
                    raise RuntimeError('Pilot inputs changed; use a new experiment version')
                state['in_progress']=True;save(state)
                tick(state)
            except Exception as ex:
                state.update(status='needs_review',error=str(ex))
            finally:state['in_progress']=False
        save(state)
        subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/official/report.py')],check=False)
        if state.get('status') in ['complete','needs_review']:
            subprocess.run(['systemctl','stop','gemma-lab-official-pilot.timer'],check=False)
        print(json.dumps(state),flush=True)


if __name__ == '__main__':
    main()
