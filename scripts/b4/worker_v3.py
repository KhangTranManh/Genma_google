"""B4 v3 (31B): per-region Patch calls + public corpus v2 + adaptive sampling + one feedback round.

Each region (excerpt) gets its own Patch call on the cumulative source, told which issue functions use it.
Feedback round: only regions whose functions are still slow (or every region if tests/behavior fail).
  .venv/bin/python scripts/b4/worker_v3.py --model 31b
"""
from pathlib import Path
import argparse,fcntl,hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
import worker as w1,worker_v2 as w2
EXP=w1.EXP;guard=w1.guard;chat=w1.chat;dump=w1.dump;OFFICIAL=w1.OFFICIAL
SAMPLES=w2.SAMPLES[:6];TASKS=w1.TASKS;RUN='b4-v3'


def evaluate(tid,src,folder):
    folder.mkdir(parents=True,exist_ok=True);(folder/'candidate-source.txt').write_text(src)
    subprocess.run([OFFICIAL,str(HERE/'evaluate.py'),'--corpus','v2','--task',tid,'--source',str(folder/'candidate-source.txt'),'--out',str(folder/'eval')],check=True,timeout=1800,capture_output=True)
    return json.loads((folder/'eval/evaluation.json').read_text())


def region_note(funcs,n_regions):
    return (f'This excerpt is used by: {", ".join(funcs)}. '+('It is one of '+str(n_regions)+' separately supplied excerpts; repair THIS excerpt now (other excerpts are handled in separate calls).' if n_regions>1 else ''))


def patch_region(model,folder,cases,spec,diag,src,ri,temp,seed,tools,history=None):
    a,b=spec['regions'][ri];region=guard.Region(a,b);block=w1.excerpts(src,[spec['regions'][ri]]);funcs=spec['region_functions'][ri]
    issue=spec['issue']+'\n\n'+region_note(funcs,len(spec['regions']))
    if history is None:user=w1.patch_prompt(cases,issue,diag,block,spec['file'])
    else:user=w2.feedback_prompt(cases,issue,diag,block,spec['file'],history)
    return w1.guarded(model,folder,[{'role':'system','content':cases['patch_system']},{'role':'user','content':user}],src,spec['file'],[region],temp,seed,tools)


def main(model):
    base=ROOT/'runs'/RUN/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True);tasks=json.loads((EXP/'tasks.json').read_text());cases=json.loads((ROOT/'experiments/b23_v1/cases.json').read_text());tools=json.loads((EXP/'tools.json').read_text())
    state={'status':'running','model':model,'max_samples':len(SAMPLES),'corpus':'v2','completed':[],'selection':{}}
    def save():dump(base/'state.json',state);report(model)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list(HERE.glob('*.py'))+[p for p in EXP.rglob('*') if p.is_file()]+[ROOT/'scripts/harness/edit_guard.py',ROOT/'scripts/b23/worker.py',ROOT/'experiments/b23_v1/cases.json',ROOT/'experiments/methods/30-b4-v3.md']
        dump(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()});save()
        try:
            w1.start(model)
            for tid in TASKS:
                spec=tasks[tid];src0=(EXP/tid/'original.py').read_text();nreg=len(spec['regions'])
                cal=json.loads((EXP/tid/'calibration.json').read_text());timing={k:round(v,4) for k,v in list(cal['original_medians'].items())[:3] if v is not None}
                selected=None
                for s in SAMPLES:
                    f=base/tid/s['id'];state['current']=f'{tid}/{s["id"]}';save();row={'task':tid,'sample':s['id'],'rounds':[]}
                    blocks=w1.excerpts(src0,spec['regions'])
                    d=chat(model,[{'role':'system','content':cases['diagnose_system']},{'role':'user','content':w1.diagnose_prompt(spec['issue'],blocks,timing,spec['repro']['expr'].replace('N','n'))}],f/'diagnose',512,s['temperature'],s.get('seed'))
                    text=d['content'] or '';m=re.search(r'\{.*\}',text,re.S)
                    try:diag=json.dumps(json.loads(m.group(0)),ensure_ascii=False) if m else text.strip()
                    except json.JSONDecodeError:diag=text.strip()
                    cur=src0;ev=None
                    for rnd in range(2):
                        if rnd==0:targets=list(range(nreg))
                        else:
                            slow={k for k,v in ev['public']['reproducer'].get('per_function',{}).items() if not v['passed']} if ev else set()
                            other_fail=ev is None or not ev['public']['functional_tests']['passed'] or not ev['public']['differential']['passed']
                            targets=[i for i in range(nreg) if other_fail or set(spec['region_functions'][i])&slow]
                        guards=[]
                        for ri in targets:
                            hist=None
                            if rnd==1:hist=[{'attempt':0,'public_results':w2.public_view(ev)} if ev else {'attempt':0,'result':'no applicable edit in the previous attempt'}]
                            seed=None if s.get('seed') is None else s['seed']+100*rnd+ri
                            after,gs,ng=patch_region(model,f/f'round{rnd}'/f'region{ri}',cases,spec,diag,cur,ri,s['temperature'],seed,tools,hist)
                            guards.append(gs)
                            if after is not None:cur=after
                        r={'round':rnd,'regions':targets,'guards':guards}
                        if cur!=src0:ev=evaluate(tid,cur,f/f'round{rnd}');r.update(w2.row_from(ev))
                        row['rounds'].append(r)
                        if ev and ev['public_pass']:break
                    final=row['rounds'][-1];row.update(final_public_pass=bool(final.get('public_pass')),final_accepted=bool(final.get('accepted_audit')),accepted_round0=bool(row['rounds'][0].get('accepted_audit')))
                    if row['final_public_pass']:selected=s['id'];row['selected']=True
                    state['completed'].append(row);save()
                    if selected:break
                state['selection'][tid]={'selected':selected,'selected_accepted':next((r['final_accepted'] for r in state['completed'] if r['task']==tid and r.get('selected')),None),'samples_used':sum(1 for r in state['completed'] if r['task']==tid)};save()
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()


def report(model):
    base=ROOT/'runs'/RUN/model;out=ROOT/'reports'/RUN/model;out.mkdir(parents=True,exist_ok=True)
    st=json.loads((base/'state.json').read_text()) if (base/'state.json').exists() else {}
    lines=[f'# B4 v3 — {model.upper()}','',f"Trạng thái: `{st.get('status')}`",'','| task | sample | round | regions | guards | perf per function | tests | diff | public | accepted (audit) |','|---|---|---|---|---|---|---|---|---|---|']
    for r in st.get('completed',[]):
        for x in r['rounds']:lines.append(f"| {r['task']} | {r['sample']} | {x['round']} | {x['regions']} | {x['guards']} | {x.get('perf_per_function','')} | {x.get('public_tests','')} | {x.get('public_diff','')} | {x.get('public_pass','')} | {x.get('accepted_audit','')} |")
    if st.get('selection'):lines+=['','## Chọn theo public','']+[f'- {t}: {v}' for t,v in st['selection'].items()]
    (out/'summary.md').write_text('\n'.join(lines)+'\n');dump(out/'state.json',st)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['31b']);main(p.parse_args().model)
