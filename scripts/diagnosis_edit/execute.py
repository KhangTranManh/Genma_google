import json,argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,grade,dump
from execute import valid
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.tools.workspace import edit_file

def main(model,attempt,final=False):
    base=ROOT/'runs/diagnosis-edit-v1'/model/'feedback'/f'attempt_{attempt}';manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        if final:
            folder=base/'final-independent';folder.mkdir();cid=setup(manager)
            manager.get_sandbox(cid).write_file('w3lib/html.py',(base/'api/after-source.txt').read_text())
            grade(manager,cid,folder);return
        classification=json.loads((base/'classification.json').read_text());calls_by_kind={'raw':classification.get('independent_native_calls',[]),'api':json.loads((base/'parsed-calls.json').read_text())};results={}
        before=(ROOT/'experiments/diagnosis_edit_v1/source.txt').read_text() if attempt==0 else (base.parent/f'attempt_{attempt-1}'/'api/after-source.txt').read_text()
        (base/'before-source.txt').write_text(before)
        for label,calls in calls_by_kind.items():
            folder=base/label;folder.mkdir();cid=setup(manager);manager.get_sandbox(cid).write_file('w3lib/html.py',before)
            result={'call_valid':valid(calls),'tool_result':{'status':'error','error_message':'Expected exactly one valid edit_file call'}}
            if result['call_valid']:
                ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5)
                result.update(tool_result=json.loads(edit_file(ctx,**calls[0]['arguments'])),old_string_literal_match=calls[0]['arguments']['old_string'] in before)
            after=manager.exec(cid,'cat w3lib/html.py').stdout;(folder/'after-source.txt').write_text(after)
            (folder/'cumulative.patch').write_text(manager.exec(cid,'git diff HEAD').stdout)
            result['file_changed_this_attempt']=after!=before
            manager.copy_to(cid,ROOT/'scripts/diagnosis_edit/public_check.py','/tmp')
            public=manager.exec(cid,'timeout 20s python /tmp/public_check.py');(folder/'public-diagnostic.txt').write_text(public.stdout+'\n'+public.stderr)
            try:diagnostic=json.loads(public.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError):diagnostic={'passed':False,'error':'No valid public diagnostic output'}
            tests=manager.exec(cid,'timeout 60s python -m pytest tests/test_html.py -q');(folder/'public-tests.txt').write_text(tests.stdout+'\n'+tests.stderr)
            result['public_feedback']={'tool_result':result['tool_result'],'diagnostic':diagnostic,'functional_tests':{'command':'python -m pytest tests/test_html.py -q','exit_code':tests.exit_code,'stdout':tests.stdout,'stderr':tests.stderr},'passed':bool(diagnostic.get('passed') and tests.exit_code==0)}
            results[label]=result
        dump(base/'execution.json',results);print(model,attempt,{k:v['public_feedback']['passed'] for k,v in results.items()},flush=True)
    finally:manager.cleanup_all()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--attempt',required=True,type=int);p.add_argument('--final',action='store_true');a=p.parse_args();main(a.model,a.attempt,a.final)
