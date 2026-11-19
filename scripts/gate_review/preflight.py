import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,grade,dump
from swegemma.sandbox import ContainerManager,ContainerConfig

def main():
    out=ROOT/'reports/gate-review-v1/preflight'
    if out.exists():raise FileExistsError('Preserve grader preflight')
    out.mkdir(parents=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for label in ['baseline','diagnostic_fixed']:
            cid=setup(manager);folder=out/label;folder.mkdir()
            if label=='diagnostic_fixed':
                source=(ROOT/'experiments/role_split_v1/source.txt').read_text();a=source.index('_baseurl_re');b=source.index('_meta_refresh_re',a);manager.get_sandbox(cid).write_file('w3lib/html.py',source[:a]+source[a:b].replace('[^>]*','[^<>]*',1)+source[b:])
            manager.copy_to(cid,ROOT/'scripts/role_split/public_check.py','/tmp');manager.copy_to(cid,ROOT/'scripts/feedback_edit/public_check.py','/tmp/role_perf.py')
            p=manager.exec(cid,'timeout 100s python /tmp/public_check.py');public=json.loads(p.stdout.strip().splitlines()[-1]);dump(folder/'public.json',public)
            independent=grade(manager,cid,folder)
            code='from w3lib.html import get_base_url\nimport json\nprint(json.dumps({"passed":all(get_base_url(\'<base data-other="\'+"x"*n+\'" href="https://example.org/a/">\')=="https://example.org/a/" for n in [300,1500])}))\n'
            manager.get_sandbox(cid).write_file('_audit_preflight.py',code);r=manager.exec(cid,'timeout 20s python _audit_preflight.py');sem=json.loads(r.stdout.strip().splitlines()[-1]);results[label]={'public':public,'independent':independent,'semantics':sem}
        baseline=results['baseline'];fixed=results['diagnostic_fixed'];usable=not baseline['public']['passed'] and baseline['public']['functional']['exit_code']==0 and baseline['semantics']['passed'] and not baseline['independent']['verified_local_fix'] and fixed['public']['passed'] and fixed['independent']['verified_local_fix'] and fixed['semantics']['passed']
        dump(out/'summary.json',{'usable':usable,'results':results});print('Audit grader preflight usable:',usable)
        if not usable:raise RuntimeError('Audit grader not validated')
    finally:manager.cleanup_all()
if __name__=='__main__':main()
