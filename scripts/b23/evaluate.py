"""Grade one candidate source for w3lib_264 (run with .venv-official). Writes <out>/evaluation.json.

public (harness may use; shown to model in B2 feedback): reproducer perf, 67 functional tests, public differential.
hidden (grader only): independent regression grader, long-attribute semantic check, hidden differential.
accepted = public_pass and all hidden checks.
--timing additionally measures the ORIGINAL reproducer at 1000/2000/4000 (public info for Diagnose).
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));from repair_strategy_semantic_audit import CHECK as SEMANTIC
sys.path.insert(0,str(ROOT/'scripts/graders'));from differential_runner import check as differential,ORIGINAL,REFERENCE
sys.path.insert(0,str(ROOT/'scripts/infer_edit'));from grading import setup,grade,dump
from swegemma.sandbox import ContainerManager,ContainerConfig
TIMING='''import time,json,sys
from w3lib.html import get_base_url
out={}
for n in [1000,2000,4000]:
    s="<base "*n;t=time.perf_counter();get_base_url(s);out[str(n)]=round(time.perf_counter()-t,4)
print(json.dumps(out))'''


def last_json(r,default):
    try:return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):return default


def evaluate(source,folder,timing=False):
    folder.mkdir(parents=True,exist_ok=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        cid=setup(manager);sb=manager.get_sandbox(cid);sb.write_file('w3lib/html.py',source)
        manager.copy_to(cid,ROOT/'scripts/hint_ladder_v2/public_check.py','/tmp')
        perf=last_json(manager.exec(cid,'timeout 20s python /tmp/public_check.py'),{'passed':False,'error':'no output'})
        g=grade(manager,cid,folder)
        sb.write_file('_semantic_check.py',SEMANTIC);sem=last_json(manager.exec(cid,'timeout 20s python _semantic_check.py'),{'passed':False,'error':'no output'})
        t=None
        if timing:sb.write_file('_timing.py',TIMING);t=last_json(manager.exec(cid,'timeout 60s python _timing.py'),{'error':'no output'})
        d=differential(manager,cid,source)
    finally:manager.cleanup_all()
    tests=(folder/'public-tests.txt').read_text() if (folder/'public-tests.txt').exists() else ''
    public={'reproducer':perf,'functional_tests':{'passed':g['public_tests_pass'],'output_tail':tests[-3000:]},
            'differential':{'passed':d.get('public',{}).get('passed',False),'disagreements':d.get('public',{}).get('disagreements'),'examples':d.get('public',{}).get('examples',[])[:3]}}
    public_pass=bool(perf.get('passed') and g['public_tests_pass'] and public['differential']['passed'])
    hidden={'independent_regression':g['verified_local_fix'],'semantic_long_attribute':sem.get('passed'),'differential':d.get('hidden',{}).get('passed'),'differential_disagreements':d.get('hidden',{}).get('disagreements')}
    result={'public':public,'public_pass':public_pass,'hidden':hidden,'accepted':bool(public_pass and all(hidden[k] for k in ['independent_regression','semantic_long_attribute','differential'])),'timing_original':t}
    dump(folder/'evaluation.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--timing',action='store_true');a=p.parse_args()
    r=evaluate(Path(a.source).read_text(),Path(a.out),a.timing);print(json.dumps({'public_pass':r['public_pass'],'accepted':r['accepted']}))
