from pathlib import Path
import json
from swegemma.harness.container_setup import extract_snapshot,setup_git_exclude
ROOT=Path(__file__).resolve().parents[2]
def dump(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str)+'\n')
def setup(manager):
    cid=manager.start();extract_snapshot(manager,cid,ROOT/'data/freshswe/snapshots/w3lib_264.tgz');setup_git_exclude(manager,cid)
    manager.copy_to(cid,ROOT/'data/freshswe/sandbox/setup.py','/tmp')
    result=manager.exec(cid,'python /tmp/setup.py scrapy/w3lib')
    if result.exit_code:raise RuntimeError('Setup failed: '+result.stderr+result.stdout)
    return cid

def grade(manager,cid,folder):
    manager.copy_to(cid,ROOT/'scripts/infer_edit/regression_check.py','/tmp')
    public=manager.exec(cid,'timeout 60s python -m pytest tests/test_html.py -q')
    (folder/'public-tests.txt').write_text(public.stdout+'\n'+public.stderr)
    regression=manager.exec(cid,'timeout 70s python /tmp/regression_check.py')
    (folder/'regression-stdout.txt').write_text(regression.stdout+'\n'+regression.stderr)
    try:r=json.loads(regression.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):r={'passed':False,'error':'No valid regression result','inconclusive':True}
    result={'public_tests_exit_code':public.exit_code,'public_tests_pass':public.exit_code==0,'regression_exit_code':regression.exit_code,'regression':r,'verified_local_fix':public.exit_code==0 and regression.exit_code==0 and r.get('passed',False)}
    dump(folder/'grade.json',result);return result
