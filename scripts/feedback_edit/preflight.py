import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,dump
from swegemma.sandbox import ContainerManager,ContainerConfig

def main():
    out=ROOT/'reports/feedback-edit-v1';out.mkdir(parents=True,exist_ok=True);p=out/'public-preflight.json'
    if p.exists():raise FileExistsError(p)
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for label in ['baseline','diagnostic_fixed']:
            cid=setup(manager)
            if label=='diagnostic_fixed':
                source=(ROOT/'experiments/feedback_edit_v1/source.txt').read_text();a=source.index('_baseurl_re =');b=source.index('_meta_refresh_re',a);source=source[:a]+source[a:b].replace('[^>]*','[^<>]*',1)+source[b:];manager.get_sandbox(cid).write_file('w3lib/html.py',source)
            manager.copy_to(cid,ROOT/'scripts/feedback_edit/public_check.py','/tmp')
            r=manager.exec(cid,'timeout 20s python /tmp/public_check.py');results[label]=json.loads(r.stdout.strip().splitlines()[-1])
        usable=not results['baseline']['passed'] and results['diagnostic_fixed']['passed'] and not results['baseline'].get('error');dump(p,{'usable':usable,'results':results});print('public diagnostic preflight',usable)
        if not usable:raise RuntimeError('Public check not validated')
    finally:manager.cleanup_all()
if __name__=='__main__':main()
