import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,grade,dump
from execute import valid
from swegemma.sandbox import ContainerManager,ContainerConfig
from swegemma.context import SwegemmaContext
from swegemma.tools.workspace import edit_file

def main(model,case):
    base=ROOT/'runs/gate-audit-v1'/model/'audit'/case
    if (base/'outcome.json').exists():raise FileExistsError('Preserve measured outcome')
    calls=json.loads((base/'parsed-calls.json').read_text());classification=json.loads((base/'classification.json').read_text());outcome={'attempt_status':'scorable','verified_patch_pass':False,'call_valid':valid(calls),'capture_label':classification['label'],'raw_equals_api':classification.get('native_equals_api'),'reason':None}
    if classification['label']=='missing_raw_capture':raise RuntimeError('Capture infrastructure missing raw IDs')
    if classification['label']=='truncated' or not valid(calls):outcome['reason']='truncated_or_invalid_generation';dump(base/'outcome.json',outcome);return
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'))
    try:
        cid=setup(manager);ctx=SwegemmaContext(docker_manager=manager,container_id=cid,max_tool_calls=10,max_time_minutes=5);response=json.loads(edit_file(ctx,**calls[0]['arguments']));outcome['tool_result']=response
        diff=manager.exec(cid,'git diff HEAD');(base/'candidate.patch').write_text(diff.stdout)
        if response.get('status')!='ok':outcome['reason']='tool_edit_failed';dump(base/'outcome.json',outcome);return
        # Host-owned public observations, same grader as role split; no feedback to model.
        manager.copy_to(cid,ROOT/'scripts/role_split/public_check.py','/tmp')
        manager.copy_to(cid,ROOT/'scripts/feedback_edit/public_check.py','/tmp/role_perf.py')
        obs=manager.exec(cid,'timeout 100s python /tmp/public_check.py');(base/'public-output.txt').write_text(obs.stdout+'\n'+obs.stderr)
        public=json.loads(obs.stdout.strip().splitlines()[-1]);outcome['public_observations']=public
        if public.get('infrastructure_error'):raise RuntimeError('Public observation infrastructure error')
        g=grade(manager,cid,base)
        code='from w3lib.html import get_base_url\nimport json\ncases=[]\nfor n in [300,1500]:\n s=\'<base data-other="\'+"x"*n+\'" href="https://example.org/a/">\'\n cases.append(get_base_url(s)=="https://example.org/a/")\nprint(json.dumps({"passed":all(cases),"cases":cases}))\n'
        manager.get_sandbox(cid).write_file('_audit_semantics.py',code);result=manager.exec(cid,'timeout 20s python _audit_semantics.py');extra=json.loads(result.stdout.strip().splitlines()[-1]);outcome.update(independent_grade=g,additional_semantics=extra)
        if g['regression_exit_code']!=0 or g['regression'].get('inconclusive'):raise RuntimeError('Independent grader result unavailable')
        outcome['verified_patch_pass']=bool(diff.stdout and public['passed'] and g['verified_local_fix'] and extra['passed']);outcome['reason']='verified_pass' if outcome['verified_patch_pass'] else 'behavioral_tests_failed'
        dump(base/'outcome.json',outcome)
    finally:manager.cleanup_all()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--case',required=True);a=p.parse_args();main(a.model,a.case)
