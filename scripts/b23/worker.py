"""B2 (31B self-diagnosis + generic checklist + public-differential feedback) and
B3 (12B sampling + harness filtering). One batch per invocation; separate dirs/state/reports.

  .venv/bin/python scripts/b23/worker.py --batch b3   # 12B
  .venv/bin/python scripts/b23/worker.py --batch b2   # 31B
"""
from pathlib import Path
import argparse,copy,fcntl,hashlib,importlib.util,json,re,subprocess,sys,time,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'));from gemma_lab.config import load
sys.path.insert(0,str(ROOT/'scripts/official'));from start_reading_model_v2 import start
spec=importlib.util.spec_from_file_location('edit_guard',ROOT/'scripts/harness/edit_guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
EXP=ROOT/'experiments/b23_v1';OFFICIAL=str(ROOT/'.venv-official/bin/python')
REGION=guard.Region('_baseurl_re =','_meta_refresh_re');FILE='w3lib/html.py'
BATCH={'b2':{'model':'31b','dir':'b2-selfdiag-v1'},'b3':{'model':'12b','dir':'b3-sampling-v1'}}


def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')


def normalize(calls):
    out=[]
    for c in calls or []:
        fn=c.get('function',c);args=fn.get('arguments',{})
        if isinstance(args,str):
            try:args=json.loads(args)
            except json.JSONDecodeError:args={'__invalid_json__':args}
        out.append({'name':fn.get('name'),'arguments':args})
    return out


def chat(model,messages,folder,max_tokens,temperature,seed=None,tools=None):
    if folder.exists():raise FileExistsError('Preserve previous capture: '+str(folder))
    alias=load(ROOT/'configs/project.toml').raw['models'][model]['alias']
    served=json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/models',timeout=5))
    if not any(m['id']==alias and m.get('max_model_len')==16384 for m in served['data']):raise RuntimeError('Wrong model is served')
    req={'model':alias,'messages':messages,'temperature':temperature,'max_tokens':max_tokens,'stream':False,'return_token_ids':True,'skip_special_tokens':False,'chat_template_kwargs':{'enable_thinking':False}}
    if tools:req.update(tools=tools,tool_choice='auto')
    if seed is not None:req['seed']=seed
    folder.mkdir(parents=True);dump(folder/'request.json',req);t=time.monotonic()
    r=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',data=json.dumps(req).encode(),headers={'Content-Type':'application/json'}),timeout=240))
    dump(folder/'response.json',r);ch=r['choices'][0];ids=ch.get('token_ids') or []
    out={'content':ch['message'].get('content'),'calls':normalize(ch['message'].get('tool_calls')),'finish_reason':ch.get('finish_reason'),'output_tokens':len(ids),'prompt_tokens':r.get('usage',{}).get('prompt_tokens'),'seconds':round(time.monotonic()-t,2)}
    dump(folder/'result.json',out);return out


def evaluate(source,folder,timing=False):
    folder.mkdir(parents=True,exist_ok=True);(folder/'candidate-source.txt').write_text(source)
    subprocess.run([OFFICIAL,str(HERE/'evaluate.py'),'--source',str(folder/'candidate-source.txt'),'--out',str(folder)]+(['--timing'] if timing else []),check=True,timeout=900,capture_output=True)
    return json.loads((folder/'evaluation.json').read_text())


def block(src):
    a=src.find('_baseurl_re');b=src.find('_meta_refresh_re',max(a,0));return src[a:b] if a>=0 and b>a else src[:6000]


def guarded_patch(model,folder,messages,source,temperature,seed,tools):
    """One repair attempt with the B1 guard (at most one mechanical re-ask)."""
    n=[0]
    def gen(notice):
        msgs=copy.deepcopy(messages)
        if notice:msgs[-1]['content']+='\n\n'+notice
        r=chat(model,msgs,folder/f'gen{n[0]}',1536,temperature,None if seed is None else seed+n[0],tools);n[0]+=1;return r['calls']
    g=guard.guarded_call(gen,source,FILE,REGION)
    rec={'guard_status':g.check['status'],'guard_events':[{k:v for k,v in e.items() if k!='calls'} for e in g.events],'generations':g.generations,'final_calls':g.calls}
    dump(folder/'guard.json',rec);return g.check.get('after'),rec


def public_feedback_view(ev):
    p=ev['public'];return {'reproducer':p['reproducer'],'functional_tests':p['functional_tests'],'behavior_vs_original':{'passed':p['differential']['passed'],'disagreements':p['differential']['disagreements'],
        'examples (input, original output, your output)':[{'input':e['text'],'baseurl':e['baseurl'],'original':e['original'],'yours':e['candidate']} for e in p['differential']['examples']]}}


# ---------------- B2: 31B ----------------
def b2(base,cases,state,save):
    model='31b';tools=json.loads((EXP/'tools.json').read_text());issue=(ROOT/'experiments/infer_edit_v1/issue-sanitized.md').read_text();src0=(EXP/'source.txt').read_text()
    timing=json.loads((base/'preflight/original/evaluation.json').read_text())['timing_original']
    for arm in cases['b2']['arms']:
        for traj in cases['b2']['trajectories']:
            tid=f"{arm}/{traj['id']}";t=base/arm/traj['id'];state['current']=tid;save();row={'arm':arm,'traj':traj['id']}
            temp,seed=traj['temperature'],traj.get('seed')
            if arm=='selfdiag_G':
                msg=[{'role':'system','content':cases['diagnose_system']},{'role':'user','content':cases['diagnose_user'].format(issue=issue,source=block(src0),timing=json.dumps(timing))}]
                d=chat(model,msg,t/'diagnose',512,temp,seed);text=d['content'] or ''
                m=re.search(r'\{.*\}',text,re.S);diag=None
                try:diag=json.loads(m.group(0)) if m else None
                except json.JSONDecodeError:diag=None
                row.update(diagnosis_parsed=diag is not None,diagnosis_truncated=d['finish_reason']=='length')
                first=('Diagnosis (written by a separate analysis step of this system; it may be wrong):\n'+(json.dumps(diag,ensure_ascii=False) if diag else text.strip()))
            else:first=cases['hints']['A']
            hints=first+'\n\n'+cases['hints']['G']
            sys_msg=cases['patch_system'];src=src0;history=[]
            for rnd in range(cases['b2']['max_rounds']):
                if rnd==0:user=cases['patch_user'].format(issue=issue,hints=hints,source=block(src))
                else:user=cases['feedback_user'].format(issue=issue,hints=hints,history=json.dumps(history,ensure_ascii=False),source=block(src))
                after,g=guarded_patch(model,t/f'round{rnd}',[{'role':'system','content':sys_msg},{'role':'user','content':user}],src,temp,seed,tools)
                r={'round':rnd,'guard':g['guard_status'],'generations':g['generations']}
                if after is None:r.update(public_pass=False,accepted=False);row.setdefault('rounds',[]).append(r);history.append({'attempt':rnd,'call':g['final_calls'],'result':'edit rejected: '+g['guard_status']});continue
                ev=evaluate(after,t/f'round{rnd}/eval');r.update(public_pass=ev['public_pass'],accepted=ev['accepted'],pattern=block(after).strip()[:160]);row.setdefault('rounds',[]).append(r)
                src=after
                if ev['public_pass']:break
                history.append({'attempt':rnd,'call':g['final_calls'],'public_feedback':public_feedback_view(ev)})
            row['final_public_pass']=row['rounds'][-1]['public_pass'];row['final_accepted']=row['rounds'][-1]['accepted'];row['accepted_round0']=row['rounds'][0]['accepted']
            state['completed'].append(row);save()


# ---------------- B3: 12B ----------------
def b3(base,cases,state,save):
    model='12b';tools=json.loads((EXP/'tools.json').read_text());src0=(EXP/'source.txt').read_text()
    for prompt in cases['b3']['prompts']:
        selected=None
        for seed in cases['b3']['seeds']:
            sid=f"{prompt['id']}/s{seed}";f=base/prompt['id']/f's{seed}';state['current']=sid;save()
            after,g=guarded_patch(model,f,[{'role':'system','content':cases['patch_system']},{'role':'user','content':prompt['instruction']}],src0,cases['b3']['temperature'],seed,tools)
            row={'prompt':prompt['id'],'seed':seed,'guard':g['guard_status'],'generations':g['generations'],'guard_reasked':bool(g['guard_events'])}
            if after is not None:
                ev=evaluate(after,f/'eval');row.update(pattern=block(after).strip()[:160],perf=ev['public']['reproducer'].get('passed'),tests=ev['public']['functional_tests']['passed'],public_diff=ev['public']['differential']['passed'],public_pass=ev['public_pass'],accepted_audit=ev['accepted'])
            else:row.update(public_pass=False,accepted_audit=False)
            if selected is None and row['public_pass']:selected=seed;row['selected']=True
            state['completed'].append(row);save()
        state.setdefault('selection',{})[prompt['id']]={'selected_seed':selected,'selected_accepted':next((r['accepted_audit'] for r in state['completed'] if r['prompt']==prompt['id'] and r.get('selected')),None)};save()


def main(batch):
    cfg=BATCH[batch];model=cfg['model'];base=ROOT/'runs'/cfg['dir']/model
    if (base/'state.json').exists():raise FileExistsError('Preserve existing batch: '+str(base))
    base.mkdir(parents=True,exist_ok=True);cases=json.loads((EXP/'cases.json').read_text())
    state={'status':'running','batch':batch,'model':model,'completed':[]}
    def save():dump(base/'state.json',state);report(batch)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=list(HERE.glob('*.py'))+list(EXP.glob('*'))+[ROOT/'scripts/harness/edit_guard.py',ROOT/'scripts/graders/w3lib_264_differential.py',ROOT/'scripts/graders/differential_runner.py',ROOT/'experiments/methods/27-b2-b3.md',ROOT/'experiments/infer_edit_v1/issue-sanitized.md',ROOT/'scripts/infer_edit/grading.py',ROOT/'scripts/infer_edit/regression_check.py',ROOT/'scripts/hint_ladder_v2/public_check.py',ROOT/'data/freshswe/snapshots/w3lib_264.tgz']
        dump(base/'frozen-inputs.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()});save()
        try:
            state['current']='preflight';save();src0=(EXP/'source.txt').read_text()
            sys.path.insert(0,str(ROOT/'scripts/graders'))
            ref=src0[:src0.index('_baseurl_re =')]+block(src0).replace('[^>]*','[^<>]*',1)+src0[src0.index('_meta_refresh_re'):]
            o=evaluate(src0,base/'preflight/original',timing=True);r=evaluate(ref,base/'preflight/reference')
            usable=(not o['public_pass']) and o['hidden']['differential'] and r['accepted'];dump(base/'preflight/summary.json',{'usable':usable})
            if not usable:raise RuntimeError('Preflight failed')
            start(model);(b2 if batch=='b2' else b3)(base,cases,state,save)
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()


def report(batch):
    cfg=BATCH[batch];model=cfg['model'];base=ROOT/'runs'/cfg['dir']/model;out=ROOT/'reports'/cfg['dir']/model;out.mkdir(parents=True,exist_ok=True)
    st=json.loads((base/'state.json').read_text()) if (base/'state.json').exists() else {}
    rows=st.get('completed',[]);lines=[f"# {cfg['dir']} — {model.upper()}",'',f"Trạng thái: `{st.get('status')}`",'']
    if rows:
        keys=list(dict.fromkeys(k for r in rows for k in r if k!='rounds'))
        lines+=['| '+' | '.join(keys)+' |','|'+'---|'*len(keys)]+['| '+' | '.join(str(r.get(k,'')) for k in keys)+' |' for r in rows]
        if any('rounds' in r for r in rows):
            lines+=['','## Các vòng','']+[f"- {r['arm']}/{r['traj']} r{x['round']}: guard={x['guard']} gen={x['generations']} public={x['public_pass']} accepted={x['accepted']} `{x.get('pattern','').splitlines()[1].strip() if x.get('pattern') and len(x['pattern'].splitlines())>1 else ''}`" for r in rows for x in r.get('rounds',[])]
    if st.get('selection'):lines+=['','Chọn theo public: `'+json.dumps(st['selection'])+'`']
    (out/'summary.md').write_text('\n'.join(lines)+'\n');dump(out/'state.json',st)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',required=True,choices=['b2','b3']);main(p.parse_args().batch)
