from pathlib import Path
import sys,json,fcntl,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2]
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def main():
    base=ROOT/'runs/edit-excerpt-v1';base.mkdir(parents=True,exist_ok=True)
    state={'status':'running','completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/edit_excerpt').glob('*.py'))+list((ROOT/'experiments/edit_excerpt_v1').glob('*'))+[ROOT/'scripts/probes_stress/native_nested.py',ROOT/'scripts/probes_stress/length_calibration.py']
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n');save()
        try:
            for model in ['12b','31b']:
                state['current']=model;save();start(model);run(model,'excerpt','exact_excerpt')
                subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/edit_excerpt/execute.py'),'--model',model],check=True,timeout=180)
                state['completed'].append(model);save()
            state['status']='complete'
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()
if __name__=='__main__':main()
