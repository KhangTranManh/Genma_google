from pathlib import Path
import subprocess,json
from repair_strategy_report import generate
ROOT=Path(__file__).resolve().parents[1]
def main():
    base=ROOT/'runs/repair-strategies-v1';base.mkdir(parents=True,exist_ok=True)
    if (base/'state.json').exists():raise FileExistsError('Preserve existing controller')
    state={'status':'running','completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n');generate()
    save()
    try:
        for module,run in [('budget_edit','feedback-budget-v1'),('diagnosis_edit','diagnosis-edit-v1'),('candidates_edit','candidates-edit-v1')]:
            state['current']=run;save()
            with (base/(run+'.log')).open('w') as log:subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts'/module/'worker.py')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600)
            state['completed'].append(run);save()
        state['status']='complete'
    except Exception as e:state.update(status='needs_review',error=repr(e));raise
    finally:save()
if __name__=='__main__':main()
