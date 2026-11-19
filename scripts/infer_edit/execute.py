import json,argparse
from pathlib import Path
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.tools.workspace import edit_file
from grading import ROOT,setup,grade,dump

def valid(calls):
    if len(calls)!=1 or calls[0].get('name')!='edit_file':return False
    a=calls[0].get('arguments',{})
    return isinstance(a,dict) and a.get('filepath')=='w3lib/html.py' and all(isinstance(a.get(k),str) for k in ['old_string','new_string']) and bool(a['old_string']) and set(a)<=set(['filepath','old_string','new_string','allow_multiple']) and ('allow_multiple' not in a or isinstance(a['allow_multiple'],bool))
def main(model,arm,case_id):
    base=ROOT/'runs/infer-edit-v1'/model/arm/case_id;source=(ROOT/'experiments/infer_edit_v1/source.txt').read_text();classification=json.loads((base/'classification.json').read_text());native=classification.get('independent_native_calls',[]);api=json.loads((base/'parsed-calls.json').read_text());results={}
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        for label,calls in [('raw',native),('api',api)]:
            folder=base/label;folder.mkdir()
            if not valid(calls):results[label]={'executed':False,'category':'invalid_call' if calls else 'no_supported_call'};continue
            args=calls[0]['arguments'];cid=setup(manager);ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5)
            response=json.loads(edit_file(ctx,**args));content=manager.exec(cid,'cat w3lib/html.py').stdout
            diff=manager.exec(cid,'git diff HEAD');(folder/'executed.patch').write_text(diff.stdout)
            result={'executed':True,'tool_result':response,'old_string_literal_match':args['old_string'] in source,'file_changed':content!=source}
            if response.get('status')!='ok':result['category']='old_string_mismatch' if not result['old_string_literal_match'] else 'tool_error'
            else:
                g=grade(manager,cid,folder);result['grade']=g
                result['category']='verified_local_fix' if g['verified_local_fix'] and result['file_changed'] else ('inconclusive_grader' if g['regression'].get('error') or g['regression_exit_code']!=0 else ('applied_but_tests_fail' if not g['public_tests_pass'] else 'applied_but_regression_fail'))
            results[label]=result
        dump(base/'execution.json',results);print(model,arm,case_id,{k:v.get('category') for k,v in results.items()},flush=True)
    finally:manager.cleanup_all()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--arm',required=True);p.add_argument('--case',required=True);a=p.parse_args();main(a.model,a.arm,a.case)
