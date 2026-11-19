from pathlib import Path
import sys,json,fcntl,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
from report import generate
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start
from capture import run

def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    base=ROOT/'runs/toolcall-stress-v1';base.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/probes_stress').glob('*.py'))+list((ROOT/'experiments/toolcall_stress_v1').glob('*.json'))+[ROOT/'configs/toolcall-stress.toml']
        save(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        state={'status':'running','tools_executed':0,'completed':[]}
        cases=json.loads((ROOT/'experiments/toolcall_stress_v1/cases.json').read_text())
        try:
            for model in ['12b','31b']:
                start(model)
                for arm,items in cases.items():
                    for case in items:
                        state['current']={'model':model,'arm':arm,'case':case['id']};save(base/'state.json',state)
                        path=base/model/arm/case['id']/'classification.json'
                        result=json.loads(path.read_text()) if path.exists() else run(model,arm,case['id'])
                        if result['label']=='missing_raw_capture':raise RuntimeError('Missing raw capture')
                        if arm=='long_direct' and not result.get('length_validated'):raise RuntimeError('Context calibration mismatch')
                        state['completed'].append(result);save(base/'state.json',state);generate()
            state['status']='complete'
        except Exception as e:
            state.update(status='needs_review',error=repr(e));raise
        finally:
            state['updated_at']=datetime.now(timezone.utc).isoformat();save(base/'state.json',state);generate()
if __name__=='__main__':main()
