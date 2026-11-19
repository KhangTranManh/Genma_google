from pathlib import Path
import json,hashlib,fcntl,sys,subprocess
ROOT=Path(__file__).resolve().parents[2]
from audit_report import generate
from capture import run
sys.path.insert(0,str(ROOT/'scripts/official'))
from start_reading_model_v2 import start

def main():
    base=ROOT/'runs/gate-audit-v1';base.mkdir(parents=True,exist_ok=True)
    if (base/'state.json').exists():raise FileExistsError('Preserve batch')
    state={'status':'running','completed':[]}
    def save():(base/'state.json').write_text(json.dumps(state,indent=2)+'\n');generate()
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest=json.loads((ROOT/'experiments/gate_review_v1/audit-manifest.json').read_text())
        for p,h in manifest['source_hashes'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise RuntimeError('Archived ranking changed')
        for p in ['reports/gate-review-v1/preflight/summary.json','runs/role-split-v1/evidence/preflight.json','reports/infer-edit-v1/preflight/summary.json']:
            if not json.loads((ROOT/p).read_text()).get('usable'):raise RuntimeError('Grader preflight not validated')
        files=list((ROOT/'scripts/gate_review').glob('*.py'))+list((ROOT/'experiments/gate_review_v1').glob('*'))+list((ROOT/'configs/gate-review').glob('*.toml'))+[ROOT/'scripts/role_split/public_check.py',ROOT/'scripts/feedback_edit/public_check.py',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/infer_edit/execute.py',ROOT/'scripts/probes_stress/native_nested.py',ROOT/'data/freshswe/snapshots/w3lib_264.tgz',ROOT/'configs/project.toml',ROOT/'configs/reading-runtime-v2.toml',ROOT/'reports/gate-review-v1/preflight/summary.json']
        (base/'frozen-inputs.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n');save()
        try:
            for model in ['12b','31b']:
                start(model)
                for row in [r for r in manifest['records'] if r['model']==model]:
                    case=row['record_id'].replace('/','__');state['current']=row['record_id'];save();run(model,'audit',case)
                    subprocess.run([str(ROOT/'.venv-official/bin/python'),str(ROOT/'scripts/gate_review/execute_audit.py'),'--model',model,'--case',case],check=True,timeout=240)
                    state['completed'].append(row['record_id']);save()
            state['status']='complete'
        except Exception as ex:state.update(status='needs_review',error=repr(ex));raise
        finally:save()
if __name__=='__main__':main()
