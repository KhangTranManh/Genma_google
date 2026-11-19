"""Post-hoc semantic audit, kept separate from frozen experimental graders."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,dump
from swegemma.sandbox import ContainerManager,ContainerConfig
CHECK='''from w3lib.html import get_base_url
import json
cases=[]
for n in [0,200,1000]:
 html='<base data-extra="'+'x'*n+'" href="https://example.org/path/">'
 actual=get_base_url(html)
 cases.append({"attribute_length":n,"expected":"https://example.org/path/","actual":actual,"passed":actual=="https://example.org/path/"})
print(json.dumps({"cases":cases,"passed":all(c["passed"] for c in cases)}))
'''
def main():
    out=ROOT/'reports/repair-strategies-v1';out.mkdir(parents=True,exist_ok=True);manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));rows=[]
    try:
        selections=[('baseline','baseline',None)]
        for arm in ['feedback-budget-v1','diagnosis-edit-v1','candidates-edit-v1']:
            for model in ['12b','31b']:
                finals=list((ROOT/'runs'/arm/model).glob('feedback/*/final-independent/grade.json'))
                if finals:selections.append((arm,model,finals[0].parent.parent/'api/after-source.txt'))
        for arm,model,source in selections:
            cid=setup(manager)
            if source:manager.get_sandbox(cid).write_file('w3lib/html.py',source.read_text())
            manager.get_sandbox(cid).write_file('_posthoc_semantic_audit.py',CHECK)
            r=manager.exec(cid,'timeout 20s python _posthoc_semantic_audit.py')
            try:result=json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError):result={'passed':False,'error':r.stderr+r.stdout}
            rows.append({'arm':arm,'model':model,'posthoc_semantic_audit':result})
        dump(out/'posthoc-semantic-audit.json',{'status':'post_hoc_after_observing_A12b_bounded_regex','used_for_selection':False,'source':'ordinary valid base tag with additional attribute lengths0/200/1000','results':rows})
        print(json.dumps(rows,indent=2))
    finally:manager.cleanup_all()
if __name__=='__main__':main()
