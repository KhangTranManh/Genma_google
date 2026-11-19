from pathlib import Path
import sys,json,fcntl,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2]
from capture import run
import importlib.util
report_spec=importlib.util.spec_from_file_location('context_prompt_report',ROOT/'scripts/context_prompt/report.py')
report_module=importlib.util.module_from_spec(report_spec);report_spec.loader.exec_module(report_module)
generate=report_module.generate
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def main():
    base=ROOT/'runs/context-prompt-v1';base.mkdir(parents=True,exist_ok=True)
    state={'status':'running','completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/context_prompt').glob('*.py'))+list((ROOT/'experiments/context_prompt_v1').glob('*'))+[ROOT/'scripts/probes_stress/native_nested.py',ROOT/'experiments/methods/17-context-prompt.md']
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n');save()
        cases=json.loads((ROOT/'experiments/context_prompt_v1/cases.json').read_text())
        try:
            for model in ['31b','12b']:
                start(model)
                for case in ['short','4k','12k']:
                    for arm in ['control','careful']:
                        state['current']={'model':model,'case':case,'arm':arm};save();r=run(model,arm,case)
                        if case!='short' and not r.get('length_validated'):raise RuntimeError('Input length mismatch')
                        subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/context_prompt/execute.py'),'--model',model,'--arm',arm,'--case',case],check=True,timeout=180)
                        state['completed'].append(state['current']);save();generate()
            state['status']='complete'
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save();generate()
if __name__=='__main__':main()
