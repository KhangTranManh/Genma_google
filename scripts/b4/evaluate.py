"""Grade one candidate for a B4 task (run with .venv-official).

public (harness may use; may be shown to the model): reproducer median <= limit at N_public, the repo's
  existing tests/test_html.py, public differential vs ORIGINAL on plain HTML.
hidden (grader only): upstream tests (test_patch applied), growth check at 4 sizes, hidden differential.
accepted = public_pass and all hidden checks.
"""
from pathlib import Path
import argparse,json,sys
import os
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/os.environ.get('B4_EXP','experiments/b4_v1')
from swegemma.harness.container_setup import extract_snapshot,setup_git_exclude
from swegemma.sandbox import ContainerManager,ContainerConfig
CHECK=ROOT/'scripts/b4/container_check.py'
CORPUS='v1'


def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str)+'\n')
def last_json(r,default):
    try:return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):return dict(default,stderr=(r.stderr or '')[-1500:])


def setup(manager,tid,spec):
    cid=manager.start();extract_snapshot(manager,cid,ROOT/'data/freshswe/snapshots'/f'{tid}.tgz');setup_git_exclude(manager,cid)
    manager.copy_to(cid,ROOT/'data/freshswe/sandbox/setup.py','/tmp')
    r=manager.exec(cid,'python /tmp/setup.py '+spec['repo'])
    if r.exit_code:raise RuntimeError('Setup failed: '+r.stderr+r.stdout)
    manager.copy_to(cid,CHECK,'/tmp');return cid


def perf_cmd(spec,sizes,timeout=3,part=None):
    rp=part or spec['repro']
    return ('python /tmp/container_check.py perf --setup '+json.dumps(rp['setup'])+' --expr '+json.dumps(rp['expr'])+' --check '+json.dumps(rp['check'])+
            f' --sizes {",".join(map(str,sizes))} --timeout {timeout}')


def evaluate(tid,source,folder):
    tasks=json.loads((EXP/'tasks.json').read_text());spec=tasks[tid];cal=json.loads((EXP/tid/'calibration.json').read_text())
    folder.mkdir(parents=True,exist_ok=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:'+tid))
    try:
        cid=setup(manager,tid,spec);sb=manager.get_sandbox(cid);sb.write_file(spec['file'],source)
        sb.write_file('_orig_mod.py',(EXP/tid/'original.py').read_text());sb.write_file('_ref_mod.py',(EXP/tid/'reference.py').read_text())
        pub_perf=last_json(manager.exec(cid,'timeout 60s '+perf_cmd(spec,[cal['public_n']],timeout=3)),{'error':'no output'})
        m=pub_perf.get('medians',{}).get(str(cal['public_n']));pub_perf['passed']=m is not None and m<=cal['public_limit'] and not pub_perf.get('timeouts') and not pub_perf.get('error')
        parts={}
        for part in spec.get('repro_parts',[]):
            n=cal.get('parts',{}).get(part['name'],{}).get('public_n',cal['public_n'])
            r=last_json(manager.exec(cid,'timeout 60s '+perf_cmd(spec,[n],timeout=3,part=part)),{'error':'no output'});pm=r.get('medians',{}).get(str(n))
            parts[part['name']]={'expr':part['expr'].replace('N',str(n)),'median_seconds':pm,'timed_out':bool(r.get('timeouts')),'error':r.get('error'),'passed':pm is not None and pm<=cal['public_limit'] and not r.get('timeouts') and not r.get('error')}
        if parts:pub_perf['per_function']=parts;pub_perf['passed']=bool(pub_perf['passed'] and all(v['passed'] for v in parts.values()))
        tests=manager.exec(cid,'timeout 120s python -m pytest tests/test_html.py -q -p no:cacheprovider');(folder/'public-tests.txt').write_text(tests.stdout+'\n'+tests.stderr)
        module=spec['file'][:-3].replace('/','.')
        d=last_json(manager.exec(cid,'timeout 600s python /tmp/container_check.py diff --module '+module+" --calls '"+json.dumps(spec['diff_calls']).replace("'","'\\''")+"' --orig _orig_mod.py --ref _ref_mod.py --corpus "+CORPUS),{'public':{'passed':False},'hidden':{'passed':False}})
        sizes=cal['growth_sizes'];g=last_json(manager.exec(cid,'timeout 120s '+perf_cmd(spec,sizes,timeout=3)),{'error':'no output'})
        med=g.get('medians',{});small=med.get(str(sizes[0]));mid=med.get(str(sizes[2]));large=med.get(str(sizes[-1]))
        growth=(mid/max(small,0.005)) if small is not None and mid is not None else None
        g.update(growth_4x=growth,passed=bool(large is not None and large<=0.5 and growth is not None and growth<=8 and not g.get('timeouts') and not g.get('error')))
        manager.copy_to(cid,EXP/tid/'test.patch','/tmp');ap=manager.exec(cid,'git apply /tmp/test.patch')
        up=manager.exec(cid,'timeout 300s python -m pytest tests/test_html.py -q -p no:cacheprovider');(folder/'upstream-tests.txt').write_text(ap.stderr+'\n'+up.stdout+'\n'+up.stderr)
    finally:manager.cleanup_all()
    public={'reproducer':pub_perf,'functional_tests':{'passed':tests.exit_code==0,'output_tail':(tests.stdout+tests.stderr)[-2500:]},
            'differential':{'passed':d.get('public',{}).get('passed',False),'disagreements':d.get('public',{}).get('disagreements'),'examples':d.get('public',{}).get('examples',[])}}
    public_pass=bool(pub_perf['passed'] and public['functional_tests']['passed'] and public['differential']['passed'])
    hidden={'upstream_tests':ap.exit_code==0 and up.exit_code==0,'growth':g,'differential':d.get('hidden',{}).get('passed',False),'differential_disagreements':d.get('hidden',{}).get('disagreements'),'differential_meta':{k:d.get(k) for k in ['n_cases','n_plain','n_calls','n_slow','seconds']}}
    r={'task':tid,'public':public,'public_pass':public_pass,'hidden':hidden,'accepted':bool(public_pass and hidden['upstream_tests'] and g['passed'] and hidden['differential'])}
    dump(folder/'evaluation.json',r);return r


def calibrate(tid):
    """Time the ORIGINAL reproducer at several sizes; choose N_public where the original takes >= 0.5 s."""
    spec=json.loads((EXP/'tasks.json').read_text())[tid];manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:'+tid))
    try:
        cid=setup(manager,tid,spec);sizes=spec.get('cal_sizes',[1000,2000,4000,8000,16000])
        r=last_json(manager.exec(cid,'timeout 200s '+perf_cmd(spec,sizes,timeout=10)),{'error':'no output'})
    finally:manager.cleanup_all()
    med=r['medians'];n=next((s for s in sizes if med.get(str(s)) and med[str(s)]>=0.5),None)
    if n is None:raise RuntimeError(f'{tid}: original never reached 0.5 s: {med}')
    base=n//4
    out={'original_medians':med,'public_n':n,'public_limit':0.2,'growth_sizes':[base,base*2,base*4,base*15]}
    parts={}
    for part in spec.get('repro_parts',[]):
        manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:'+tid))
        try:
            cid=setup(manager,tid,spec);pr=last_json(manager.exec(cid,'timeout 300s '+perf_cmd(spec,sizes,timeout=10,part=part)),{'error':'no output'})
        finally:manager.cleanup_all()
        pmed=pr['medians'];pn=next((s for s in sizes if pmed.get(str(s)) and pmed[str(s)]>=0.5),None) or next((s for s in sizes if pmed.get(str(s)) is None),sizes[-1])
        parts[part['name']]={'original_medians':pmed,'public_n':pn}
    out['parts']=parts
    dump(EXP/tid/'calibration.json',out);print(tid,out,flush=True)

def calibrate_parts(tid):
    """Add per-function public N to an existing calibration without changing the v1 fields."""
    spec=json.loads((EXP/'tasks.json').read_text())[tid];path=EXP/tid/'calibration.json';cal=json.loads(path.read_text());sizes=spec.get('cal_sizes',[1000,2000,4000,8000,16000]);parts={}
    for part in spec.get('repro_parts',[]):
        manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:'+tid))
        try:
            cid=setup(manager,tid,spec);pr=last_json(manager.exec(cid,'timeout 300s '+perf_cmd(spec,sizes,timeout=10,part=part)),{'error':'no output'})
        finally:manager.cleanup_all()
        pmed=pr['medians'];pn=next((s for s in sizes if pmed.get(str(s)) is not None and pmed[str(s)]>=0.5),None) or next((s for s in sizes if pmed.get(str(s)) is None),sizes[-1])
        parts[part['name']]={'original_medians':pmed,'public_n':pn}
    cal['parts']=parts;dump(path,cal);print(tid,parts,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--calibrate',action='store_true');p.add_argument('--calibrate-parts',action='store_true');p.add_argument('--source');p.add_argument('--out');p.add_argument('--corpus',default='v1',choices=['v1','v2','v3']);a=p.parse_args();CORPUS=a.corpus
    if a.calibrate:calibrate(a.task)
    elif a.calibrate_parts:calibrate_parts(a.task)
    else:r=evaluate(a.task,Path(a.source).read_text(),Path(a.out));print(json.dumps({'public_pass':r['public_pass'],'accepted':r['accepted']}))
