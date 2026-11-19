"""B4: transfer check on sibling regex-performance issues. One batch per model.

Per task and sample: Diagnose (self, JSON) -> Patch (diagnosis + frozen checklist G, B1 multi-edit guard).
Harness selects the first sample (fixed order) that passes all public checks; hidden checks graded for audit only.
  .venv/bin/python scripts/b4/worker.py --model 31b
"""
from pathlib import Path
import argparse,copy,fcntl,hashlib,importlib.util,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];EXP=ROOT/'experiments/b4_v1'
sys.path.insert(0,str(ROOT/'scripts/official'));from start_reading_model_v2 import start
spec=importlib.util.spec_from_file_location('b23_worker',ROOT/'scripts/b23/worker.py');b23=importlib.util.module_from_spec(spec);spec.loader.exec_module(b23)
guard=b23.guard;chat=b23.chat;dump=b23.dump
OFFICIAL=str(ROOT/'.venv-official/bin/python')
SAMPLES={'31b':[{'id':'t0','temperature':0},{'id':'s17','temperature':0.6,'seed':17},{'id':'s29','temperature':0.6,'seed':29},{'id':'s43','temperature':0.6,'seed':43}],
         '12b':[{'id':'t0','temperature':0}]+[{'id':f's{s}','temperature':0.6,'seed':s} for s in (17,29,43,5,11)]}
TASKS=['w3lib_266','w3lib_268','w3lib_271']


def excerpts(src,regions):
    out=[]
    for a,b in regions:
        i=src.find(a);j=src.find(b,i+1);out.append(src[i:j].rstrip('\n')+'\n')
    return out


def render(blocks):
    return '\n'.join(f'BEGIN_SOURCE {k+1}\n{b}END_SOURCE {k+1}' for k,b in enumerate(blocks))


def patch_prompt(cases,issue,diag,blocks,filepath):
    n=len(blocks)
    work=('Work carefully on the supplied source excerpts only. Infer a minimal repair from the issue. Before emitting a call, check internally that old_string occurs verbatim in the source, '
          'that backslashes, quotes, spaces and newlines are preserved, and that the replacement preserves the intended behavior outside the reported defect. Do not reconstruct unrelated code. '
          f'Emit one edit_file call for {filepath} for each excerpt you change (at most {n}). Do not read files, run commands, explain, or retry. This driver will execute and evaluate the calls independently.')
    return (f'Issue:\n{issue}\n\nAnalysis (use it as guidance):\n\nDiagnosis (written by a separate analysis step of this system; it may be wrong):\n{diag}\n\n{cases["hints"]["G"]}\n\n{work}\n\n'
            f'Exact current source excerpts from {filepath}:\n{render(blocks)}\n')


def diagnose_prompt(issue,blocks,timing,expr):
    return (f'Issue:\n{issue}\n\nSource excerpts:\n{render(blocks)}\n\nPublic measurement of the ORIGINAL code, seconds for {expr} at several N: {json.dumps(timing)}\n\n'
            'Explain the cause. Reply with exactly one JSON object with keys:\n"span": the exact part of the code responsible,\n"failing_condition": the inputs on which matching fails and becomes slow,\n'
            '"complexity": the growth you infer from the measurements,\n"why": a short mechanism explanation (at most 4 sentences).')


def guarded(model,folder,messages,src,filepath,regions,temp,seed,tools):
    calls_log=[];status=None;after=None
    for attempt in range(2):
        msgs=copy.deepcopy(messages)
        if attempt and status:msgs[-1]['content']+='\n\nHost notice (not a grader result): '+status['message']
        r=chat(model,msgs,folder/f'gen{attempt}',1536,temp,None if seed is None else seed+attempt,tools)
        status=guard.check_edits(r['calls'],src,filepath,regions);calls_log.append({'gen':attempt,'status':status['status'],'finish':r['finish_reason'],'calls':r['calls']})
        if status['status']=='ok':after=status['after'];break
        if status['status'] not in guard.RETRYABLE:break
    dump(folder/'guard.json',{'final_status':status['status'],'generations':len(calls_log),'log':calls_log});return after,status['status'],len(calls_log)


def main(model):
    base=ROOT/'runs/b4-v1'/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True);tasks=json.loads((EXP/'tasks.json').read_text());cases=json.loads((ROOT/'experiments/b23_v1/cases.json').read_text())
    tools=json.loads((EXP/'tools.json').read_text());state={'status':'running','model':model,'tasks':TASKS,'samples':[s['id'] for s in SAMPLES[model]],'completed':[],'selection':{}}
    def save():dump(base/'state.json',state);report(model)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list(HERE.glob('*.py'))+[p for p in EXP.rglob('*') if p.is_file()]+[ROOT/'scripts/harness/edit_guard.py',ROOT/'scripts/b23/worker.py',ROOT/'experiments/b23_v1/cases.json',ROOT/'experiments/methods/28-b4-transfer.md']+[ROOT/'data/freshswe/snapshots'/f'{t}.tgz' for t in TASKS]
        dump(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()});save()
        try:
            for t in TASKS:
                if not json.loads((ROOT/'runs/b4-preflight-v1'/t/'reference/evaluation.json').read_text())['accepted']:raise RuntimeError('Preflight failed for '+t)
            start(model)
            for tid in TASKS:
                spec=tasks[tid];src=(EXP/tid/'original.py').read_text();blocks=excerpts(src,spec['regions']);regions=[guard.Region(a,b) for a,b in spec['regions']]
                cal=json.loads((EXP/tid/'calibration.json').read_text());timing={k:round(v,4) for k,v in list(cal['original_medians'].items())[:3] if v is not None}
                selected=None
                for s in SAMPLES[model]:
                    f=base/tid/s['id'];state['current']=f'{tid}/{s["id"]}';save();row={'task':tid,'sample':s['id']}
                    d=chat(model,[{'role':'system','content':cases['diagnose_system']},{'role':'user','content':diagnose_prompt(spec['issue'],blocks,timing,spec['repro']['expr'].replace('N','n'))}],f/'diagnose',512,s['temperature'],s.get('seed'))
                    text=d['content'] or '';m=re.search(r'\{.*\}',text,re.S)
                    try:diag=json.dumps(json.loads(m.group(0)),ensure_ascii=False) if m else text.strip()
                    except json.JSONDecodeError:diag=text.strip()
                    row['diagnosis_json']=diag.startswith('{')
                    msgs=[{'role':'system','content':cases['patch_system']},{'role':'user','content':patch_prompt(cases,spec['issue'],diag,blocks,spec['file'])}]
                    after,gs,ng=guarded(model,f/'patch',msgs,src,spec['file'],regions,s['temperature'],s.get('seed'),tools);row.update(guard=gs,generations=ng)
                    if after is not None:
                        (f/'candidate-source.txt').write_text(after)
                        subprocess.run([OFFICIAL,str(HERE/'evaluate.py'),'--task',tid,'--source',str(f/'candidate-source.txt'),'--out',str(f/'eval')],check=True,timeout=1800,capture_output=True)
                        ev=json.loads((f/'eval/evaluation.json').read_text());h=ev['hidden']
                        row.update(public_perf=ev['public']['reproducer']['passed'],public_tests=ev['public']['functional_tests']['passed'],public_diff=ev['public']['differential']['passed'],public_pass=ev['public_pass'],
                                   hidden_upstream=h['upstream_tests'],hidden_growth=h['growth']['passed'],hidden_diff=h['differential'],accepted_audit=ev['accepted'])
                    else:row.update(public_pass=False,accepted_audit=False)
                    if selected is None and row['public_pass']:selected=s['id'];row['selected']=True
                    state['completed'].append(row);save()
                state['selection'][tid]={'selected':selected,'selected_accepted':next((r['accepted_audit'] for r in state['completed'] if r['task']==tid and r.get('selected')),None)};save()
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()


def report(model):
    base=ROOT/'runs/b4-v1'/model;out=ROOT/'reports/b4-v1'/model;out.mkdir(parents=True,exist_ok=True)
    st=json.loads((base/'state.json').read_text()) if (base/'state.json').exists() else {};rows=st.get('completed',[])
    lines=[f'# B4 transfer — {model.upper()}','',f"Trạng thái: `{st.get('status')}`",'']
    if rows:
        keys=list(dict.fromkeys(k for r in rows for k in r))
        lines+=['| '+' | '.join(keys)+' |','|'+'---|'*len(keys)]+['| '+' | '.join(str(r.get(k,'')) for k in keys)+' |' for r in rows]
    if st.get('selection'):lines+=['','## Chọn theo public','']+[f'- {t}: {v}' for t,v in st['selection'].items()]
    (out/'summary.md').write_text('\n'.join(lines)+'\n');dump(out/'state.json',st)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['12b','31b']);main(p.parse_args().model)
