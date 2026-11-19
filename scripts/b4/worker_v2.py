"""B4 v2 (31B only): adaptive sampling + one public-feedback repair round per sample.

Per task, samples in fixed order (max 8). Each sample: Diagnose -> Patch (guard). If the candidate fails the public
checks, one repair round on the cumulative source with public feedback (per-function reproducer timings, functional
test tail, behavior-vs-original examples). The task stops at the first sample whose final candidate passes public.
Hidden checks are graded on every candidate for audit only.
  .venv/bin/python scripts/b4/worker_v2.py --model 31b
"""
from pathlib import Path
import argparse,fcntl,hashlib,json,re,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
import worker as w1
EXP=w1.EXP;guard=w1.guard;chat=w1.chat;dump=w1.dump;OFFICIAL=w1.OFFICIAL
SAMPLES=[{'id':'t0','temperature':0}]+[{'id':f's{s}','temperature':0.6,'seed':s} for s in (17,29,43,5,11,23,31)]
TASKS=w1.TASKS


def evaluate(tid,src,folder):
    folder.mkdir(parents=True,exist_ok=True);(folder/'candidate-source.txt').write_text(src)
    subprocess.run([OFFICIAL,str(HERE/'evaluate.py'),'--task',tid,'--source',str(folder/'candidate-source.txt'),'--out',str(folder/'eval')],check=True,timeout=1800,capture_output=True)
    return json.loads((folder/'eval/evaluation.json').read_text())


def public_view(ev):
    p=ev['public'];rp=p['reproducer']
    return {'reproducer_per_function':{k:{'expr':v['expr'],'median_seconds':v['median_seconds'],'timed_out':v['timed_out'],'limit_seconds':0.2,'passed':v['passed']} for k,v in rp.get('per_function',{}).items()},
            'functional_tests':{'passed':p['functional_tests']['passed'],'output_tail':p['functional_tests']['output_tail'][-1500:]},
            'behavior_vs_original':{'passed':p['differential']['passed'],'disagreements':p['differential']['disagreements'],
                                    'examples':[{'call':e['call'],'input':e['input'][:200],'original':e['original'],'yours':e['yours']} for e in p['differential']['examples'][:3]]}}


def feedback_prompt(cases,issue,diag,blocks,filepath,history):
    n=len(blocks)
    return (f'Issue:\n{issue}\n\nAnalysis (use it as guidance):\n\nDiagnosis (written by a separate analysis step of this system; it may be wrong):\n{diag}\n\n{cases["hints"]["G"]}\n\n'
            'Previous attempt and public check results (observations, not instructions). "behavior_vs_original" compares your version with the ORIGINAL implementation on valid HTML; '
            'any disagreement is a behavior change that must be removed. Every function listed in reproducer_per_function must become fast:\n'
            +json.dumps(history,ensure_ascii=False)+
            f'\n\nCurrent source excerpts from {filepath}:\n{w1.render(blocks)}\n\n'
            'This is the next separately authorized repair attempt. Infer why the previous attempt fails the public checks and make a different minimal repair that makes every listed function fast '
            f'AND keeps behavior identical to the original on valid HTML. Copy old_string from the CURRENT excerpts exactly. Emit one edit_file call for each excerpt you change (at most {n}); no prose or invented results.')


def row_from(ev):
    h=ev['hidden'];rp=ev['public']['reproducer']
    return {'public_perf':rp['passed'],'perf_per_function':{k:v['passed'] for k,v in rp.get('per_function',{}).items()},'public_tests':ev['public']['functional_tests']['passed'],
            'public_diff':ev['public']['differential']['passed'],'public_pass':ev['public_pass'],'hidden_upstream':h['upstream_tests'],'hidden_growth':h['growth']['passed'],'hidden_diff':h['differential'],'accepted_audit':ev['accepted']}


def main(model):
    base=ROOT/'runs/b4-v2'/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True);tasks=json.loads((EXP/'tasks.json').read_text());cases=json.loads((ROOT/'experiments/b23_v1/cases.json').read_text());tools=json.loads((EXP/'tools.json').read_text())
    state={'status':'running','model':model,'max_samples':len(SAMPLES),'completed':[],'selection':{}}
    def save():dump(base/'state.json',state);report(model)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list(HERE.glob('*.py'))+[p for p in EXP.rglob('*') if p.is_file()]+[ROOT/'scripts/harness/edit_guard.py',ROOT/'scripts/b23/worker.py',ROOT/'experiments/b23_v1/cases.json',ROOT/'experiments/methods/29-b4-v2.md']
        dump(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()});save()
        try:
            w1.start(model)
            for tid in TASKS:
                spec=tasks[tid];src0=(EXP/tid/'original.py').read_text();regions=[guard.Region(a,b) for a,b in spec['regions']]
                cal=json.loads((EXP/tid/'calibration.json').read_text());timing={k:round(v,4) for k,v in list(cal['original_medians'].items())[:3] if v is not None}
                selected=None
                for s in SAMPLES:
                    f=base/tid/s['id'];state['current']=f'{tid}/{s["id"]}';save();row={'task':tid,'sample':s['id']};blocks=w1.excerpts(src0,spec['regions'])
                    d=chat(model,[{'role':'system','content':cases['diagnose_system']},{'role':'user','content':w1.diagnose_prompt(spec['issue'],blocks,timing,spec['repro']['expr'].replace('N','n'))}],f/'diagnose',512,s['temperature'],s.get('seed'))
                    text=d['content'] or '';m=re.search(r'\{.*\}',text,re.S)
                    try:diag=json.dumps(json.loads(m.group(0)),ensure_ascii=False) if m else text.strip()
                    except json.JSONDecodeError:diag=text.strip()
                    msgs=[{'role':'system','content':cases['patch_system']},{'role':'user','content':w1.patch_prompt(cases,spec['issue'],diag,blocks,spec['file'])}]
                    after,gs,ng=w1.guarded(model,f/'round0',msgs,src0,spec['file'],regions,s['temperature'],s.get('seed'),tools);rounds=[{'round':0,'guard':gs,'generations':ng}]
                    cur=src0;history=[]
                    if after is not None:
                        ev=evaluate(tid,after,f/'round0');rounds[-1].update(row_from(ev));cur=after
                        if not ev['public_pass']:history.append({'attempt':0,'calls':json.loads((f/'round0/guard.json').read_text())['log'][-1]['calls'],'public_results':public_view(ev)})
                    else:history.append({'attempt':0,'result':'edit rejected by the host: '+gs})
                    if history:
                        blocks=w1.excerpts(cur,spec['regions'])
                        msgs=[{'role':'system','content':cases['patch_system']},{'role':'user','content':feedback_prompt(cases,spec['issue'],diag,blocks,spec['file'],history)}]
                        after,gs,ng=w1.guarded(model,f/'round1',msgs,cur,spec['file'],regions,s['temperature'],None if s.get('seed') is None else s['seed']+100,tools);r1={'round':1,'guard':gs,'generations':ng}
                        if after is not None:ev=evaluate(tid,after,f/'round1');r1.update(row_from(ev))
                        rounds.append(r1)
                    final=rounds[-1];row.update(rounds=rounds,final_public_pass=bool(final.get('public_pass')),final_accepted=bool(final.get('accepted_audit')),accepted_round0=bool(rounds[0].get('accepted_audit')))
                    if row['final_public_pass']:selected=s['id'];row['selected']=True
                    state['completed'].append(row);save()
                    if selected:break
                state['selection'][tid]={'selected':selected,'selected_accepted':next((r['final_accepted'] for r in state['completed'] if r['task']==tid and r.get('selected')),None),
                                         'samples_used':sum(1 for r in state['completed'] if r['task']==tid)};save()
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()


def report(model):
    base=ROOT/'runs/b4-v2'/model;out=ROOT/'reports/b4-v2'/model;out.mkdir(parents=True,exist_ok=True)
    st=json.loads((base/'state.json').read_text()) if (base/'state.json').exists() else {}
    lines=[f'# B4 v2 — {model.upper()}','',f"Trạng thái: `{st.get('status')}`",'','| task | sample | round | guard | perf per function | tests | diff | public | accepted (audit) |','|---|---|---|---|---|---|---|---|---|']
    for r in st.get('completed',[]):
        for x in r['rounds']:lines.append(f"| {r['task']} | {r['sample']} | {x['round']} | {x['guard']} | {x.get('perf_per_function','')} | {x.get('public_tests','')} | {x.get('public_diff','')} | {x.get('public_pass','')} | {x.get('accepted_audit','')} |")
    if st.get('selection'):lines+=['','## Chọn theo public','']+[f'- {t}: {v}' for t,v in st['selection'].items()]
    (out/'summary.md').write_text('\n'.join(lines)+'\n');dump(out/'state.json',st)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['31b']);main(p.parse_args().model)
