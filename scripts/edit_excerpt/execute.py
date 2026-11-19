"""Execute raw and parsed call independently using organizer edit implementation."""
import json,argparse
from pathlib import Path
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.harness.container_setup import extract_snapshot,setup_git_exclude
from swegemma.tools.workspace import edit_file
ROOT=Path(__file__).resolve().parents[2]
def main(model):
    base=ROOT/'runs/edit-excerpt-v1'/model/'excerpt/exact_excerpt';source=(ROOT/'experiments/edit_excerpt_v1/source.txt').read_text();case=json.loads((ROOT/'experiments/edit_excerpt_v1/cases.json').read_text())['excerpt'][0];expected=source.replace(case['expected_arguments']['old_string'],case['expected_arguments']['new_string'],1)
    native=json.loads((base/'classification.json').read_text()).get('independent_native_calls',[]);api=json.loads((base/'parsed-calls.json').read_text());results={}
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        for label,calls in [('raw',native),('api',api)]:
            if len(calls)!=1 or calls[0]['name']!='edit_file':results[label]={'executed':False,'reason':'Not exactly one edit_file call'};continue
            args=calls[0]['arguments']
            if args.get('filepath')!='w3lib/html.py' or not set(args)<=set(['filepath','old_string','new_string','allow_multiple']):results[label]={'executed':False,'reason':'Unexpected arguments/path'};continue
            cid=manager.start();extract_snapshot(manager,cid,ROOT/'data/freshswe/snapshots/w3lib_264.tgz');setup_git_exclude(manager,cid)
            ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5)
            result=edit_file(ctx,**args);content=manager.exec(cid,'cat w3lib/html.py').stdout
            diff=manager.exec(cid,'git diff HEAD');(base/(label+'-executed.patch')).write_text(diff.stdout)
            results[label]={'executed':True,'tool_result':result,'old_string_literal_match':isinstance(args.get('old_string'),str) and args['old_string'] in source,'file_changed':content!=source,'exact_requested_result':content==expected}
        (base/'execution.json').write_text(json.dumps(results,indent=2,ensure_ascii=False,default=str)+'\n')
        print(json.dumps(results,ensure_ascii=False),flush=True)
    finally:manager.cleanup_all()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);main(p.parse_args().model)
