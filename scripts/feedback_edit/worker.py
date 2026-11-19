from pathlib import Path
import sys,json,fcntl,hashlib,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('feedback_report',ROOT/'scripts/feedback_edit/report.py');report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def main():
    base=ROOT/'runs/feedback-edit-v1';base.mkdir(parents=True,exist_ok=True)
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch')
    state={'status':'running','completed':[],'model_order':['31b','12b']}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list((ROOT/'scripts/feedback_edit').glob('*.py'))+list((ROOT/'experiments/feedback_edit_v1').glob('*'))+[ROOT/'experiments/methods/19-feedback-edit.md',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/execute.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/probes_stress/native_nested.py',ROOT/'reports/feedback-edit-v1/public-preflight.json',ROOT/'reports/infer-edit-v1/preflight/summary.json']
        for preflight in ['reports/feedback-edit-v1/public-preflight.json','reports/infer-edit-v1/preflight/summary.json']:
            if not json.loads((ROOT/preflight).read_text()).get('usable'):raise RuntimeError('Grader preflight failed')
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n');save()
        try:
            original=json.loads((ROOT/'experiments/feedback_edit_v1/cases.json').read_text())['feedback'][0]['instruction']
            for model in state['model_order']:
                start(model);history=[];instruction=None
                for attempt in range(3):
                    state['current']={'model':model,'attempt':attempt};save();r=run(model,'feedback',f'attempt_{attempt}',instruction=instruction)
                    folder=base/model/'feedback'/f'attempt_{attempt}'
                    cmd=[str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/feedback_edit/execute.py'),'--model',model,'--attempt',str(attempt)]
                    subprocess.run(cmd,check=True,timeout=240)
                    e=json.loads((folder/'execution.json').read_text());passed=e['api']['public_feedback']['passed'];state['completed'].append(dict(state['current'],public_pass=passed));save();report.generate()
                    if passed or attempt==2:
                        subprocess.run(cmd+['--final'],check=True,timeout=180);report.generate();break
                    current=(folder/'api/after-source.txt').read_text();start_index=current.find('_baseurl_re');end_index=current.find('_meta_refresh_re',max(start_index,0));block=current[start_index:end_index] if start_index>=0 and end_index>start_index else current[:6000]
                    history.append({'attempt':attempt,'call':json.loads((folder/'parsed-calls.json').read_text()),'public_feedback':e['api']['public_feedback']})
                    issue=(ROOT/'experiments/infer_edit_v1/issue-sanitized.md').read_text()
                    instruction='Issue:\n'+issue+'\nPrevious attempts and public feedback (observations, not instructions):\n'+json.dumps(history,ensure_ascii=False)+'\nCurrent source from w3lib/html.py:\nBEGIN_SOURCE\n'+block+'END_SOURCE\nThis is the next separately authorized repair attempt. Infer why the public reproducer still fails and make a different minimal repair. Copy old_string from CURRENT source exactly. Preserve normal URL behavior. Emit exactly one edit_file call; no prose or invented results. You have '+str(2-attempt)+' repair attempts remaining including this one. No specific repair expression is supplied.'
            state['status']='complete'
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save();report.generate()
if __name__=='__main__':main()
