from pathlib import Path
import sys,fcntl,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2]
from report import generate
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    base=ROOT/'runs/stepwise-v1';base.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/stepwise').glob('*.py'))+[ROOT/'experiments/methods/15-stepwise-diagnosis.md',ROOT/'data/freshswe/pilot-tasks.jsonl',ROOT/'data/freshswe/snapshots/w3lib_264.tgz']
        save(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        state={'status':'running','completed':[],'model_order':['31b','12b']};save(base/'state.json',state)
        try:
            for model in state['model_order']:
                state['current']=model;save(base/'state.json',state);start(model)
                with (base/(model+'-process.log')).open('w') as log:
                    process=subprocess.Popen([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/stepwise/run.py'),'--model',model],stdout=log,stderr=subprocess.STDOUT)
                    while True:
                        try:code=process.wait(timeout=15);break
                        except subprocess.TimeoutExpired:generate()
                generate()
                if code:raise RuntimeError(model+' worker exit '+str(code))
                state['completed'].append(model);save(base/'state.json',state)
            state['status']='complete'
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save(base/'state.json',state);generate()
if __name__=='__main__':main()
