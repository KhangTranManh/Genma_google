"""Execute raw/API calls of one capture in clean containers and grade every candidate.

Run with .venv-official. Graders are never shown to the model and never trigger retries.
--preflight grades original source and the host diagnostic fix to confirm graders discriminate.
"""
import json,argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,grade,dump
from execute import valid
sys.path.insert(0,str(ROOT/'scripts'))
from repair_strategy_semantic_audit import CHECK as SEMANTIC_CHECK
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.tools.workspace import edit_file
SOURCE=ROOT/'experiments/hint_ladder_v2/source.txt'


def evaluate(manager,cid,folder):
    """Public check + functional tests + independent grade + long-attribute semantic check, same container."""
    manager.copy_to(cid,ROOT/'scripts/hint_ladder_v2/public_check.py','/tmp')
    public=manager.exec(cid,'timeout 20s python /tmp/public_check.py');(folder/'public-diagnostic.txt').write_text(public.stdout+'\n'+public.stderr)
    try:diagnostic=json.loads(public.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):diagnostic={'passed':False,'error':'No valid public diagnostic output'}
    independent=grade(manager,cid,folder)
    manager.get_sandbox(cid).write_file('_semantic_check.py',SEMANTIC_CHECK)
    sem=manager.exec(cid,'timeout 20s python _semantic_check.py');(folder/'semantic-stdout.txt').write_text(sem.stdout+'\n'+sem.stderr)
    try:semantic=json.loads(sem.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):semantic={'passed':False,'error':'No valid semantic output'}
    result={'public_diagnostic':diagnostic,'functional_tests_pass':independent['public_tests_pass'],'independent':independent,'semantic_long_attribute':semantic,
            'public_pass':bool(diagnostic.get('passed') and independent['public_tests_pass']),
            'accepted':bool(diagnostic.get('passed') and independent['verified_local_fix'] and semantic.get('passed'))}
    dump(folder/'evaluation.json',result);return result


def preflight(model):
    out=ROOT/'runs/hint-ladder-v2'/model/'preflight';out.mkdir(parents=True)
    source=SOURCE.read_text();a=source.index('_baseurl_re =');b=source.index('_meta_refresh_re',a)
    fixed=source[:a]+source[a:b].replace('[^>]*','[^<>]*',1)+source[b:]
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for label,text in [('original',source),('diagnostic_fixed',fixed)]:
            folder=out/label;folder.mkdir();cid=setup(manager);manager.get_sandbox(cid).write_file('w3lib/html.py',text)
            results[label]=evaluate(manager,cid,folder)
    finally:manager.cleanup_all()
    usable=(not results['original']['accepted'] and not results['original']['public_diagnostic'].get('passed') and results['original']['semantic_long_attribute'].get('passed') is True
            and results['diagnostic_fixed']['accepted'])
    dump(out/'summary.json',{'usable':usable,'results':results});print(model,'preflight usable',usable,flush=True)
    if not usable:raise SystemExit(2)


def main(model,arm,before_path=None):
    base=ROOT/'runs/hint-ladder-v2'/model/arm;before=Path(before_path).read_text() if before_path else SOURCE.read_text();(base/'before-source.txt').write_text(before)
    classification=json.loads((base/'classification.json').read_text())
    calls_by_kind={'raw':classification.get('independent_native_calls',[]),'api':json.loads((base/'parsed-calls.json').read_text())};results={}
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        for label,calls in calls_by_kind.items():
            folder=base/label;folder.mkdir();result={'call_valid':valid(calls)}
            if not result['call_valid']:
                result.update(executed=False,category='invalid_call' if calls else 'no_supported_call',accepted=False);results[label]=result;continue
            cid=setup(manager);manager.get_sandbox(cid).write_file('w3lib/html.py',before)
            ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5)
            args=calls[0]['arguments'];tool=json.loads(edit_file(ctx,**args))
            after=manager.exec(cid,'cat w3lib/html.py').stdout;(folder/'after-source.txt').write_text(after)
            (folder/'executed.patch').write_text(manager.exec(cid,'git diff HEAD').stdout)
            result.update(executed=True,tool_result=tool,old_string_literal_match=args['old_string'] in before,file_changed=after!=before)
            if tool.get('status')!='ok' or not result['file_changed']:
                result.update(category='old_string_mismatch' if not result['old_string_literal_match'] else ('no_change' if tool.get('status')=='ok' else 'tool_error'),accepted=False)
            else:
                ev=evaluate(manager,cid,folder);result['evaluation']=ev;result['accepted']=ev['accepted']
                result['category']='accepted' if ev['accepted'] else ('public_performance_fail' if not ev['public_diagnostic'].get('passed') else ('functional_fail' if not ev['functional_tests_pass'] else ('independent_fail' if not ev['independent']['verified_local_fix'] else 'semantic_fail')))
            results[label]=result
        dump(base/'execution.json',results);print(model,arm,{k:v.get('category') for k,v in results.items()},flush=True)
    finally:manager.cleanup_all()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['12b','31b']);p.add_argument('--arm');p.add_argument('--before');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    preflight(a.model) if a.preflight else main(a.model,a.arm,a.before)
