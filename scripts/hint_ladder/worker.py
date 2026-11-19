"""Run the hint ladder for ONE model. Each model is its own batch, state and report.

Usage: .venv/bin/python scripts/hint_ladder/worker.py --model 12b
"""
from pathlib import Path
import argparse,sys,json,fcntl,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import importlib.util
spec=importlib.util.spec_from_file_location('hint_ladder_report',Path(__file__).resolve().parent/'report.py');report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start
ARMS=['control','A','AB','ABC']
OFFICIAL=str(ROOT/'.venv-official/bin/python');EXECUTE=str(ROOT/'scripts/hint_ladder/execute.py')


def main(model):
    base=ROOT/'runs/hint-ladder-v1'/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True)
    state={'status':'running','model':model,'arms':ARMS,'completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/hint_ladder').glob('*.py'))+list((ROOT/'experiments/hint_ladder_v1').glob('*'))+[ROOT/'experiments/methods/24-hint-ladder.md',ROOT/'configs/project.toml',ROOT/'configs/reading-runtime-v2.toml',ROOT/'data/freshswe/snapshots/w3lib_264.tgz',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/execute.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/repair_strategy_semantic_audit.py',ROOT/'scripts/probes_stress/native_nested.py']
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n');save()
        try:
            state['current']='preflight';save()
            subprocess.run([OFFICIAL,EXECUTE,'--model',model,'--preflight'],check=True,timeout=900)
            start(model)
            for arm in ARMS:
                state['current']=arm;save()
                c=run(model,arm)
                subprocess.run([OFFICIAL,EXECUTE,'--model',model,'--arm',arm],check=True,timeout=900)
                e=json.loads((base/arm/'execution.json').read_text())
                state['completed'].append({'arm':arm,'capture':c.get('label'),'output_tokens':c.get('output_tokens'),'api_category':e['api'].get('category'),'api_accepted':e['api'].get('accepted'),'raw_category':e['raw'].get('category')});save();report.generate(model)
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save();report.generate(model)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['12b','31b']);main(p.parse_args().model)
