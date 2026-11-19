from pathlib import Path
import sys,json,fcntl,hashlib,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('feedback_report',ROOT/'scripts/candidates_edit/report.py');report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def main():
    base=ROOT/'runs/candidates-edit-v1';base.mkdir(parents=True,exist_ok=True)
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch')
    state={'status':'running','completed':[],'model_order':['12b','31b']}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/candidates_edit').glob('*.py'))+list((ROOT/'experiments/candidates_edit_v1').glob('*'))+[ROOT/'experiments/methods/20-repair-strategies.md',ROOT/'experiments/infer_edit_v1/issue-sanitized.md',ROOT/'configs/project.toml',ROOT/'configs/reading-runtime-v2.toml',ROOT/'data/freshswe/snapshots/w3lib_264.tgz',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/execute.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/probes_stress/native_nested.py',ROOT/'reports/feedback-edit-v1/public-preflight.json',ROOT/'reports/infer-edit-v1/preflight/summary.json']
        for preflight in ['reports/feedback-edit-v1/public-preflight.json','reports/infer-edit-v1/preflight/summary.json']:
            if not json.loads((ROOT/preflight).read_text()).get('usable'):raise RuntimeError('Grader preflight failed')
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n');save()
        try:
            for model in state['model_order']:
                start(model);candidates=[]
                for attempt in range(3):
                    state['current']={'model':model,'attempt':attempt};save();run(model,'feedback',f'attempt_{attempt}')
                    folder=base/model/'feedback'/f'attempt_{attempt}'
                    cmd=[str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/candidates_edit/execute.py'),'--model',model,'--attempt',str(attempt)]
                    subprocess.run(cmd,check=True,timeout=240)
                    e=json.loads((folder/'execution.json').read_text());public=e['api']['public_feedback'];passed=public['passed']
                    candidates.append({'attempt':attempt,'public_pass':passed,'functional_pass':public['functional_tests']['exit_code']==0,'median_seconds':public['diagnostic'].get('median_seconds')})
                    state['completed'].append(dict(state['current'],public_pass=passed));save();report.generate()
                # Select using public observations only; hidden grade never used to rank.
                selected=min(candidates,key=lambda c:(not c['public_pass'],not c['functional_pass'],c['median_seconds'] if c['median_seconds'] is not None else float('inf'),c['attempt']))
                (base/model/'selection.json').write_text(json.dumps({'selected':selected,'candidates':candidates,'rule':'public pass, functional pass, measured runtime, attempt index; independent grade excluded'},indent=2)+'\n')
                subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/candidates_edit/execute.py'),'--model',model,'--attempt',str(selected['attempt']),'--final'],check=True,timeout=180);report.generate()
            state['status']='complete'
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save();report.generate()
if __name__=='__main__':main()
