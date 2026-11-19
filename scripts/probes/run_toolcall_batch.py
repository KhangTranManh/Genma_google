"""Eight bounded capture-only requests, serialized under the shared GPU lock."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start
from capture_toolcall import run
from toolcall_report import generate,read


def save(path,d):path.write_text(json.dumps(d,indent=2)+'\n')


def main():
    base=ROOT/'runs/toolcall-probe-v1';base.mkdir(parents=True,exist_ok=True)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/probes').glob('*.py'))+list((ROOT/'experiments/toolcall_probe_v1').glob('*.json'))+[ROOT/'configs/toolcall-probe.toml']
        fingerprints={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        save(base/'frozen-inputs.json',fingerprints)
        state={'status':'running','tools_executed':0,'model_order':['31b','12b'],'completed':[]}
        save(base/'state.json',state)
        cases=json.loads((ROOT/'experiments/toolcall_probe_v1/cases.json').read_text())
        try:
            for model in ['31b','12b']:
                start(model)
                for case in cases:
                    state['current']={'model':model,'case':case['id']};save(base/'state.json',state)
                    result=read(base/model/case['id']/'classification.json')
                    if not result:result=run(model,case['id'])
                    if result['label'] in ['missing_raw_capture','truncated']:raise RuntimeError('Incomplete capture; inspect '+model+'/'+case['id'])
                    if not read(base/model/case['id']/'runtime.json').get('same_generation_ids'):raise RuntimeError('Raw/parsed generation identity missing')
                    state['completed'].append({'model':model,'case':case['id'],'label':result['label']});save(base/'state.json',state);generate(ROOT)
            state['status']='complete'
        except Exception as error:
            state.update(status='needs_review',error=type(error).__name__+': '+str(error));raise
        finally:
            state['updated_at']=datetime.now(timezone.utc).isoformat();save(base/'state.json',state);generate(ROOT)

if __name__=='__main__':main()
