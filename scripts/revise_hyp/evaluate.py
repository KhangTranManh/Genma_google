import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,grade,dump
from execute import valid
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.tools.workspace import edit_file

def public(manager,cid,folder):
    manager.copy_to(cid,ROOT/'scripts/revise_hyp/public_check.py','/tmp')
    manager.copy_to(cid,ROOT/'scripts/feedback_edit/public_check.py','/tmp/role_perf.py')
    response=manager.exec(cid,'timeout 100s python /tmp/public_check.py');(folder/'public-output.txt').write_text(response.stdout+'\n'+response.stderr)
    try:value=json.loads(response.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):raise RuntimeError('Missing public observation: '+response.stderr)
    dump(folder/'observations.json',value);return value

def prepare():
    out=ROOT/'runs/revise-hyp-v1/evidence'
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for label in ['baseline','diagnostic_fixed']:
            folder=out/label;folder.mkdir();cid=setup(manager)
            if label=='diagnostic_fixed':
                source=(ROOT/'experiments/revise_hyp_v1/source.txt').read_text();a=source.index('_baseurl_re');b=source.index('_meta_refresh_re',a);manager.get_sandbox(cid).write_file('w3lib/html.py',source[:a]+source[a:b].replace('[^>]*','[^<>]*',1)+source[b:])
            results[label]=public(manager,cid,folder)
            manager.copy_to(cid,ROOT/'scripts/revise_hyp/probe_check.py','/tmp')
            probe=manager.exec(cid,'timeout 60s python /tmp/probe_check.py')
            (folder/'probe-output.txt').write_text(probe.stdout+'\n'+probe.stderr)
            if probe.exit_code:raise RuntimeError('Probe infrastructure error')
            measured=json.loads(probe.stdout.strip().splitlines()[-1])
            if any(v['error'] for v in measured['results'].values()):raise RuntimeError('Baseline probe failed')
            dump(folder/'probes.json',measured)
            if label=='baseline':
                manager.copy_to(cid,ROOT/'scripts/revise_hyp/coverage_check.py','/tmp')
                coverage=manager.exec(cid,'timeout 60s python /tmp/coverage_check.py');(out/'coverage-stdout.txt').write_text(coverage.stdout+'\n'+coverage.stderr)
                if coverage.exit_code:raise RuntimeError('Coverage collection failed')
                dump(out/'coverage.json',json.loads(coverage.stdout.strip().splitlines()[-1]))
        usable=not results['baseline']['passed'] and results['baseline']['functional']['exit_code']==0 and results['baseline']['semantic_guard']['passed'] and not results['baseline']['infrastructure_error'] and results['diagnostic_fixed']['passed']
        dump(out/'preflight.json',{'usable':usable,'results':results,'probes_collected':True})
        if not usable:raise RuntimeError('Preflight failed')
    finally:manager.cleanup_all()

def evaluate(model,index):
    base=ROOT/'runs/revise-hyp-v1'/model/'role_split'/f'hypothesis_{index}';c=json.loads((base/'classification.json').read_text());paths={'raw':c.get('independent_native_calls',[]),'api':json.loads((base/'parsed-calls.json').read_text())};manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for kind,calls in paths.items():
            folder=base/kind;folder.mkdir();cid=setup(manager);result={'valid_call':valid(calls)}
            if result['valid_call']:
                ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5);result['tool_result']=json.loads(edit_file(ctx,**calls[0]['arguments']))
            else:result['tool_result']={'status':'error','error_message':'No single valid edit_file call'}
            source=manager.exec(cid,'cat w3lib/html.py').stdout;(folder/'after-source.txt').write_text(source);(folder/'candidate.patch').write_text(manager.exec(cid,'git diff HEAD').stdout)
            result['observations']=public(manager,cid,folder);results[kind]=result
        dump(base/'execution.json',results)
    finally:manager.cleanup_all()

def final(model,index):
    base=ROOT/'runs/revise-hyp-v1'/model/'role_split'/f'hypothesis_{index}';out=base/'independent-final';out.mkdir();manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        cid=setup(manager);manager.get_sandbox(cid).write_file('w3lib/html.py',(base/'api/after-source.txt').read_text());result=grade(manager,cid,out)
        script='from w3lib.html import get_base_url\nimport json\ncases=[]\nfor n in [300,1500]:\n s=\'<base data-other="\'+"x"*n+\'" href="https://example.org/a/">\'\n cases.append(get_base_url(s)=="https://example.org/a/")\nprint(json.dumps({"passed":all(cases),"cases":cases}))\n'
        manager.get_sandbox(cid).write_file('_independent_semantics.py',script);r=manager.exec(cid,'timeout 20s python _independent_semantics.py')
        try:extra=json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError):extra={'passed':False,'error':r.stderr+r.stdout}
        dump(out/'verdict.json',{'frozen_regression_grade':result,'additional_semantics':extra,'verified_local_fix':bool(result['verified_local_fix'] and extra['passed'])})
    finally:manager.cleanup_all()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','evaluate','final']);p.add_argument('--model');p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='evaluate':evaluate(a.model,a.index)
    else:final(a.model,a.index)
