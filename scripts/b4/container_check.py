"""Container-side checks for B4 tasks (run from the repo root inside the task image).

perf: time an expression at several sizes in fresh subprocesses (3 samples, per-sample timeout).
diff: compare candidate functions with the ORIGINAL (public: plain cases must be equal) and, optionally,
      with the upstream REFERENCE (hidden: every case equal to original or reference).
"""
import argparse,importlib.util,json,random,statistics,string,subprocess,sys,time

WORKER='''import json,sys,time
{setup}
N=int(sys.argv[1]);t=time.perf_counter();r={expr};dt=time.perf_counter()-t
assert {check},repr(r)[:200]
print(json.dumps({{"seconds":dt}}))'''


def perf(setup,expr,check,sizes,repeats,timeout):
    code=WORKER.format(setup=setup,expr=expr,check=check);out={};timeouts=[];error=None
    for n in sizes:
        samples=[]
        for _ in range(repeats):
            try:
                p=subprocess.run([sys.executable,'-c',code,str(n)],capture_output=True,text=True,timeout=timeout)
                if p.returncode:raise RuntimeError(p.stderr[-400:])
                samples.append(json.loads(p.stdout)['seconds'])
            except subprocess.TimeoutExpired:timeouts.append(n);break
            except Exception as e:error=str(e);break
        out[str(n)]=statistics.median(samples) if len(samples)==repeats else None
    return {'medians':out,'timeouts':timeouts,'error':error}


# ---------------- corpus ----------------
SAFE=''.join(c for c in string.printable if c not in '<>"\'\x0b\x0c\r')+'\t\n'
TAGS=['a','b','p','div','meta','script','style','br','span','A','SCRIPT','Meta','noscript']


CORPUS='v1'


def val(rng,n,q,risky):
    s=''.join(rng.choice(SAFE) for _ in range(n)).replace(q,'')
    if risky:i=rng.randrange(len(s)+1);s=s[:i]+rng.choice(['<','>','a<b','x>y'])+s[i:]
    elif CORPUS in ('v2','v3') and q and rng.random()<0.25:i=rng.randrange(len(s)+1);s=s[:i]+rng.choice(['>','x>y','>>'])+s[i:]
    return s


def attrs(rng,risky):
    out=[]
    for _ in range(rng.choice([0,0,1,2,3])):
        q=rng.choice(['"',"'",'']);name=rng.choice(['id','class','data-x','href','title','content','http-equiv','src'])
        if q:out.append(f'{name}={q}{val(rng,rng.choice([0,3,15,120]),q,risky)}{q}')
        else:out.append(f'{name}='+(''.join(rng.choice(string.ascii_letters+string.digits+'-_./:') for _ in range(rng.choice([1,5,20])))))
    return ''.join(rng.choice([' ',' ','\n','\t'])+a for a in out)


def text(rng,risky):
    s=''.join(rng.choice(SAFE+'"\'') for _ in range(rng.choice([0,5,30])))
    if risky:s+=rng.choice([' a < b ',' x > y ','<','>'])
    return s


def element(rng,risky,unclosed):
    tag=rng.choice(TAGS);k=rng.random()
    if tag.lower()=='meta' and k<0.6:
        q=rng.choice(['"',"'"]);u=rng.choice(['http://example.org/next/','/rel/path','x y'])
        parts=[f'http-equiv={q}refresh{q}',f'content={q}{rng.choice(["5","0","1.5"])}; url={u}{q}']
        if rng.random()<0.5:parts.reverse()
        extra=attrs(rng,risky)
        return '<'+tag+extra+''.join(' '+p for p in parts)+('' if unclosed else rng.choice(['>','/>',' >']))
    open_='<'+tag+attrs(rng,risky)+('' if unclosed else rng.choice(['>','>',' >']))
    if tag.lower() in ('br','meta') or rng.random()<0.15:return open_ if unclosed else '<'+tag+attrs(rng,risky)+rng.choice(['/>',' />','>'])
    return open_+text(rng,risky)+('</'+tag+'>' if rng.random()<0.9 else '')


def corpus(seed,n):
    rng=random.Random(seed);cases=[]
    for ch in string.printable:
        if ch in '\x0b\x0c\r':continue
        for q in ['"',"'"]:
            if ch==q:continue
            plain=ch!='<' if CORPUS in ('v2','v3') else ch not in '<>'
            cases.append({'text':f'<p data-x={q}a{ch}b{q}>t</p><meta http-equiv="refresh" content="3; url=http://e.example/{ch if ch not in "<>" else ""}"><script data-y={q}{ch}{q}>x</script>','plain':plain})
            cases.append({'text':f'<div title={q}{ch}{q}>{ch if plain else "z"}</div><b>{ch if plain else "q"}</b>','plain':plain})
    for _ in range(n):
        k=rng.random();risky=k<0.15;unclosed=0.15<=k<0.22
        parts=[element(rng,risky,unclosed and i==0) for i in range(rng.choice([1,2,3,4]))]
        if rng.random()<0.2:parts.insert(rng.randrange(len(parts)+1),'<!-- c'+text(rng,False).replace('-','')+' -->')
        if rng.random()<0.3:parts.insert(0,text(rng,False))
        if CORPUS=='v3' and rng.random()<0.3:
            body=text(rng,False).replace(']]>','')+rng.choice(['','<b>x</b>',' &amp; ','>'])
            parts.insert(rng.randrange(len(parts)+1),'<![CDATA['+body+(']]>' if rng.random()<0.85 else ''))
        cases.append({'text':''.join(parts),'plain':not risky and not unclosed})
    return cases


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def run_call(mod,call,t):
    try:return {'ok':eval(call,{k:getattr(mod,k) for k in dir(mod) if not k.startswith('__')},{'t':t})}
    except Exception as e:return {'error':type(e).__name__}


def diff(module,calls,orig_path,ref_path,seed,n):
    cand=importlib.import_module(module);orig=load(orig_path,'_orig_mod');ref=load(ref_path,'_ref_mod') if ref_path else None
    cases=corpus(seed,n);pub=[];hid=[];slow=0;t0=time.perf_counter()
    for i,c in enumerate(cases):
        for call in calls:
            s=time.perf_counter();got=run_call(cand,call,c['text'])
            if time.perf_counter()-s>0.5:slow+=1
            want=run_call(orig,call,c['text'])
            got_j=json.dumps(got,default=repr);want_j=json.dumps(want,default=repr)
            if c['plain'] and got_j!=want_j:pub.append({'index':i,'call':call,'input':c['text'][:300],'original':want,'yours':got})
            if ref is not None and got_j!=want_j and got_j!=json.dumps(run_call(ref,call,c['text']),default=repr):hid.append({'index':i,'call':call,'plain':c['plain'],'input':c['text'][:300]})
    out={'corpus':CORPUS,'corpus_seed':seed,'n_cases':len(cases),'n_plain':sum(c['plain'] for c in cases),'n_calls':len(calls),'seconds':round(time.perf_counter()-t0,2),'n_slow':slow,
         'public':{'passed':not pub and not slow,'disagreements':len(pub),'examples':pub[:3]}}
    if ref is not None:out['hidden']={'passed':not hid and not slow,'disagreements':len(hid),'examples':hid[:3]}
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('perf');a.add_argument('--setup');a.add_argument('--expr');a.add_argument('--check');a.add_argument('--sizes');a.add_argument('--repeats',type=int,default=3);a.add_argument('--timeout',type=float,default=3)
    b=sub.add_parser('diff');b.add_argument('--corpus',default='v1',choices=['v1','v2','v3']);b.add_argument('--module');b.add_argument('--calls');b.add_argument('--orig');b.add_argument('--ref');b.add_argument('--seed',type=int,default=4);b.add_argument('--n',type=int,default=1500)
    x=p.parse_args();sys.path.insert(0,'.')
    if x.cmd=='perf':print(json.dumps(perf(x.setup,x.expr,x.check,[int(s) for s in x.sizes.split(',')],x.repeats,x.timeout)))
    else:
        CORPUS=x.corpus
        print(json.dumps(diff(x.module,json.loads(x.calls),x.orig,x.ref,x.seed,x.n),default=repr))
