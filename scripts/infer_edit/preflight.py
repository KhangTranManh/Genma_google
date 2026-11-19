from pathlib import Path
import json
from swegemma.sandbox import ContainerManager,ContainerConfig
from grading import ROOT,setup,grade,dump

def main():
    out=ROOT/'reports/infer-edit-v1/preflight'
    if out.exists():raise FileExistsError('Preserve preflight')
    out.mkdir(parents=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        for name in ['baseline','diagnostic_fixed']:
            folder=out/name;folder.mkdir();cid=setup(manager)
            if name=='diagnostic_fixed':
                source=(ROOT/'experiments/infer_edit_v1/source.txt').read_text();start=source.index('_baseurl_re =');end=source.index('_meta_refresh_re',start);block=source[start:end];fixed=source[:start]+block.replace('[^>]*','[^<>]*',1)+source[end:];manager.get_sandbox(cid).write_file('w3lib/html.py',fixed)
            results[name]=grade(manager,cid,folder)
        usable=results['baseline']['public_tests_pass'] and not results['baseline']['regression']['passed'] and not results['baseline']['regression'].get('error') and results['diagnostic_fixed']['verified_local_fix']
        dump(out/'summary.json',{'usable':usable,'results':results});print('PREFLIGHT usable=',usable,flush=True)
        if not usable:raise RuntimeError('Regression grader not validated')
    finally:manager.cleanup_all()
if __name__=='__main__':main()
