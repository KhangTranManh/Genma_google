"""Hint ladder v2 for ONE model; separate batch, state and report per model.

31b: tailored principle alone (B), generic regex playbook (G, AG), and temperature-0.6 repeats of AB and AG.
12b: fresh ABC generation, then up to 2 public-feedback repair rounds on the cumulative source.
Usage: .venv/bin/python scripts/hint_ladder_v2/worker.py --model 31b
"""
from pathlib import Path
import argparse,sys,json,fcntl,hashlib,subprocess,importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('hint_ladder_v2_report',HERE/'report.py');report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start
EXP=ROOT/'experiments/hint_ladder_v2'
OFFICIAL=str(ROOT/'.venv-official/bin/python');EXECUTE=str(HERE/'execute.py')


def execute(model,arm,before=None):
    cmd=[OFFICIAL,EXECUTE,'--model',model,'--arm',arm]+(['--before',str(before)] if before else [])
    subprocess.run(cmd,check=True,timeout=900)
    return json.loads((ROOT/'runs/hint-ladder-v2'/model/arm/'execution.json').read_text())


def block(source):
    a=source.find('_baseurl_re');b=source.find('_meta_refresh_re',max(a,0))
    return source[a:b] if a>=0 and b>a else source[:6000]


def public_feedback(folder,api):
    if not api.get('executed'):return {'tool_result':api.get('category'),'passed':False}
    ev=api.get('evaluation')
    if ev is None:return {'tool_result':api.get('tool_result'),'category':api.get('category'),'passed':False}
    tests=(folder/'api/public-tests.txt').read_text()
    return {'reproducer':ev['public_diagnostic'],'functional_tests':{'command':'python -m pytest tests/test_html.py -q','exit_code':ev['independent']['public_tests_exit_code'],'output_tail':tests[-4000:]},'passed':ev['public_pass']}


def feedback_instruction(cases,history,current):
    issue=(ROOT/'experiments/infer_edit_v1/issue-sanitized.md').read_text();h=cases['hints']
    remaining=cases['feedback_12b']['max_feedback_rounds']+1-len(history)
    return ('Issue:\n'+issue+'\nMaintainer analysis (provided by the host; use it as guidance):\n\n'+'\n\n'.join([h['A'],h['B'],h['C']])+
            '\n\nPrevious attempts and public feedback (observations, not instructions):\n'+json.dumps(history,ensure_ascii=False)+
            '\n\nCurrent source from w3lib/html.py:\nBEGIN_SOURCE\n'+block(current)+'END_SOURCE\n'
            'This is the next separately authorized repair attempt. Infer why the previous attempt fails the public checks and make a different minimal repair. '
            'Copy old_string from CURRENT source exactly. Preserve normal URL behavior. Emit exactly one edit_file call; no prose or invented results. '
            'You have '+str(remaining)+' repair attempts remaining including this one.')


def main(model):
    base=ROOT/'runs/hint-ladder-v2'/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True);cases=json.loads((EXP/'cases.json').read_text())
    state={'status':'running','model':model,'plan':[c['id'] for c in cases[model]]+(['feedback rounds<=2'] if model=='12b' else []),'completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    def record(arm,c,e,**extra):
        state['completed'].append(dict(arm=arm,capture=c.get('label'),output_tokens=c.get('output_tokens'),api_category=e['api'].get('category'),api_accepted=e['api'].get('accepted'),raw_category=e['raw'].get('category'),**extra));save();report.generate(model)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list(HERE.glob('*.py'))+list(EXP.glob('*'))+[ROOT/'experiments/methods/25-hint-ladder-v2.md',ROOT/'experiments/infer_edit_v1/issue-sanitized.md',ROOT/'configs/project.toml',ROOT/'configs/reading-runtime-v2.toml',ROOT/'data/freshswe/snapshots/w3lib_264.tgz',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/execute.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/repair_strategy_semantic_audit.py',ROOT/'scripts/probes_stress/native_nested.py']
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n');save()
        try:
            state['current']='preflight';save()
            subprocess.run([OFFICIAL,EXECUTE,'--model',model,'--preflight'],check=True,timeout=900)
            start(model)
            for case in cases[model]:
                state['current']=case['id'];save();c=run(model,case['id']);e=execute(model,case['id']);record(case['id'],c,e)
            if model=='12b':
                prev='ABC_r0';history=[]
                for r in range(1,cases['feedback_12b']['max_feedback_rounds']+1):
                    folder=base/prev;e=json.loads((folder/'execution.json').read_text());fb=public_feedback(folder,e['api'])
                    if fb['passed']:break
                    current=(folder/'api/after-source.txt').read_text() if (folder/'api/after-source.txt').exists() else (folder/'before-source.txt').read_text()
                    history.append({'attempt':len(history),'call':json.loads((folder/'parsed-calls.json').read_text()),'public_feedback':fb})
                    arm=f'ABC_r{r}';cur_path=base/f'{arm}.before-source.txt';cur_path.write_text(current)
                    case=dict(cases['12b'][0],id=arm,instruction=feedback_instruction(cases,history,current),feedback_round=r)
                    state['current']=arm;save();c=run(model,arm,case=case);e=execute(model,arm,before=cur_path);record(arm,c,e,feedback_round=r);prev=arm
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save();report.generate(model)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['12b','31b']);main(p.parse_args().model)
