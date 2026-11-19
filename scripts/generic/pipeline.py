"""Generic repair pipeline v1: no per-task hand definitions (run with .venv-official).

Per task (only the issue text and the repository snapshot are used by the pipeline):
  1. Localize  - model picks files/symbols from a source tree + grep hits of identifiers in the issue.
  2. Reproduce - model writes repro.py (exit 0 = fixed); harness checks it FAILS on the original (<=2 tries).
  3. Patch     - K samples, each one or more edit_file calls restricted to the localized excerpts (B1 guard).
  4. Public    - repro passes, and the repo's related tests gain no new failures vs the original.
  Selection: first sample (fixed order) passing public. Hidden: official FAIL_TO_PASS/PASS_TO_PASS grade on every
  applied candidate, for audit only.
  .venv-official/bin/python scripts/generic/pipeline.py --model 31b --tasks w3lib_264 ...
"""
from pathlib import Path
import argparse,ast,copy,fcntl,hashlib,importlib.util,json,re,subprocess,sys,tarfile,tempfile,time,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DATA=ROOT/'data/freshswe';EXP=ROOT/'experiments/generic_v1'
sys.path.insert(0,str(ROOT/'src'));from gemma_lab.config import load
sys.path.insert(0,str(ROOT/'scripts/official'));from start_reading_model_v2 import start
spec=importlib.util.spec_from_file_location('edit_guard',ROOT/'scripts/harness/edit_guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
from swegemma.harness.container_setup import extract_snapshot,setup_git_exclude
from swegemma.sandbox import ContainerManager,ContainerConfig
TOOLS=json.loads((ROOT/'experiments/b4_v1/tools.json').read_text())
SAMPLES=[{'id':'t0','temperature':0},{'id':'s17','temperature':0.6,'seed':17},{'id':'s29','temperature':0.6,'seed':29},{'id':'s43','temperature':0.6,'seed':43}]
MAX_ISSUE=6000;MAX_EXCERPTS=16000


def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str)+'\n')


def normalize(calls):
    out=[]
    for c in calls or []:
        fn=c.get('function',c);a=fn.get('arguments',{})
        if isinstance(a,str):
            try:a=json.loads(a)
            except json.JSONDecodeError:a={'__invalid_json__':a}
        out.append({'name':fn.get('name'),'arguments':a})
    return out


def chat(model,messages,folder,max_tokens,temperature,seed=None,tools=None):
    if folder.exists():raise FileExistsError(str(folder))
    alias=load(ROOT/'configs/project.toml').raw['models'][model]['alias']
    req={'model':alias,'messages':messages,'temperature':temperature,'max_tokens':max_tokens,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
    if tools:req.update(tools=tools,tool_choice='auto')
    if seed is not None:req['seed']=seed
    folder.mkdir(parents=True);dump(folder/'request.json',req);t=time.monotonic()
    r=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',data=json.dumps(req).encode(),headers={'Content-Type':'application/json'}),timeout=300))
    dump(folder/'response.json',r);ch=r['choices'][0]
    out={'content':ch['message'].get('content') or '','calls':normalize(ch['message'].get('tool_calls')),'finish_reason':ch.get('finish_reason'),'usage':r.get('usage'),'seconds':round(time.monotonic()-t,1)}
    dump(folder/'result.json',out);return out


# ---------------- host-side repository view (read-only, never executed on host) ----------------
class Repo:
    def __init__(self,tid):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        with tarfile.open(DATA/'snapshots'/f'{tid}.tgz') as tf:tf.extractall(self.root,filter='data')
        self.py=[p.relative_to(self.root).as_posix() for p in sorted(self.root.rglob('*.py')) if '.git' not in p.parts]
        self.src=[p for p in self.py if not re.search(r'(^|/)(tests?|testing|docs?|examples?|benchmarks?)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|setup\.py$|noxfile\.py$',p)]
        self.tests=[p for p in self.py if p not in self.src and re.search(r'(^|/)tests?/|test_',p)]

    def read(self,rel):return (self.root/rel).read_text(errors='replace')

    def tree(self,limit=200):return '\n'.join(self.src[:limit])+('' if len(self.src)<=limit else f'\n... ({len(self.src)-limit} more)')

    def grep(self,issue,limit=40):
        idents=set(re.findall(r'`([^`\n]{2,80})`',issue))|set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b',issue))|set(re.findall(r'\b([a-z_][a-z0-9_]{3,})\(',issue))|set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b',issue))
        names=set()
        for i in idents:
            for part in re.split(r'[^A-Za-z0-9_]+',i):
                if len(part)>=4 and not part.isdigit():names.add(part)
        hits=[]
        for rel in self.src:
            for n,line in enumerate(self.read(rel).splitlines(),1):
                for name in names:
                    if re.search(rf'\b(def|class)\s+{re.escape(name)}\b|^\s*{re.escape(name)}\s*=',line):hits.append(f'{rel}:{n}: {line.strip()[:120]}');break
        return hits[:limit],sorted(names)[:60]

    def symbol_span(self,rel,symbol):
        """Span (start,end) of a def/class/assignment named by symbol (dotted path or bare name), searched at any nesting
        depth; prefers a node whose qualified path ends with the given dotted path, then the shortest match."""
        try:tree=ast.parse(self.read(rel))
        except (SyntaxError,OSError):return None
        want=[x for x in symbol.replace('()','').split('.') if x];found=[]
        def walk(body,path):
            for node in body:
                nm=getattr(node,'name',None)
                if nm is None and isinstance(node,(ast.Assign,ast.AnnAssign)):
                    tg=node.targets[0] if isinstance(node,ast.Assign) else node.target;nm=getattr(tg,'id',None)
                if nm:
                    q=path+[nm]
                    if nm==want[-1]:
                        start=min([node.lineno]+[d.lineno for d in getattr(node,'decorator_list',[])])
                        found.append((q[-len(want):]==want,node.end_lineno-start,start,node.end_lineno,isinstance(node,ast.ClassDef),node))
                    walk(getattr(node,'body',[]),q)
        walk(tree.body,[])
        if not found:return None
        found.sort(key=lambda x:(not x[0],x[1]));best=found[0]
        return {'span':(best[2],best[3]),'is_class':best[4],'node':best[5]}

    def locate(self,rel,symbol):
        """Resolve a model target to (file, span); falls back to other source files when the symbol is not in rel."""
        order=([rel] if rel in self.src else [])+[f for f in self.src if f!=rel]
        for f in order:
            r=self.symbol_span(f,symbol)
            if r:return f,r
        return None,None


def excerpt_text(repo,rel,span):
    lines=repo.read(rel).splitlines(keepends=True);a,b=span;return ''.join(lines[a-1:b])


# ---------------- container ----------------
class Box:
    def __init__(self,tid,repo_name):
        self.m=ContainerManager(ContainerConfig(image='gemma-official-pilot:'+tid.lower()));self.cid=self.m.start()
        extract_snapshot(self.m,self.cid,DATA/'snapshots'/f'{tid}.tgz');setup_git_exclude(self.m,self.cid)
        self.m.copy_to(self.cid,DATA/'sandbox/setup.py','/tmp');r=self.m.exec(self.cid,'python /tmp/setup.py '+repo_name)
        if r.exit_code:raise RuntimeError('setup failed: '+(r.stderr+r.stdout)[-1500:])
        self.sb=self.m.get_sandbox(self.cid)

    def reset(self):self.m.exec(self.cid,'git checkout -q -- .')

    def write(self,rel,text):self.sb.write_file(rel,text)

    def run(self,cmd,timeout):r=self.m.exec(self.cid,f'timeout {timeout}s '+cmd);return r.exit_code,(r.stdout or '')+(r.stderr or '')

    def diff(self):return self.m.exec(self.cid,'git diff HEAD').stdout

    def close(self):self.m.cleanup_all()


def run_repro(box,script):
    box.m.exec(box.cid,'mkdir -p _harness');box.write('_harness/repro.py',script)
    t=time.monotonic();code,out=box.run('python _harness/repro.py',90);return {'exit_code':code,'seconds':round(time.monotonic()-t,2),'output_tail':out[-1500:]}


ENV_ERRORS=('ModuleNotFoundError','ImportError','SyntaxError','IndentationError','NameError','FileNotFoundError','PermissionError','TimeoutError')


def repro_verdict(rr):
    """valid only if it fails on the original for a reason other than the script's own environment/syntax errors."""
    if rr['exit_code']==0:return False,'it exited 0 on the current (unfixed) code, so it does not reproduce the defect'
    if rr['exit_code'] in (None,124):return False,'it timed out (90 s)'
    last=[l for l in rr['output_tail'].strip().splitlines() if l.strip()][-1:] or ['']
    for e in ENV_ERRORS:
        if last[0].startswith(e) or f'{e}:' in last[0]:return False,f'it failed with {last[0][:200]!r}, an error of the script itself (e.g. a module that is not installed); use only the package under test and the standard library'
    return True,''


def related_tests(repo,files,limit=4):
    mods=set()
    for f in files:
        p=f[:-3].split('/')
        if p and p[0]=='src':p=p[1:]
        if p[-1]=='__init__':p=p[:-1]
        if p:mods.add('.'.join(p));mods.add(p[-1])
    scored=[]
    for t in repo.tests:
        txt=repo.read(t);score=sum(1 for m in mods if re.search(rf'\b{re.escape(m)}\b',txt))
        name=Path(t).stem.replace('test_','')
        if any(name==m.split('.')[-1] for m in mods):score+=3
        if score:scored.append((score,t))
    return [t for _,t in sorted(scored,key=lambda x:(-x[0],x[1]))[:limit]]


def run_tests(box,tests):
    if not tests:return {'ran':False,'failed':set(),'exit_code':None,'output_tail':''}
    code,out=box.run('python -m pytest -q -p no:cacheprovider -rfE '+' '.join(tests),420)
    failed=set(re.findall(r'^FAILED (\S+)',out,re.M))|set(re.findall(r'^ERROR (\S+)',out,re.M))
    return {'ran':True,'failed':failed,'exit_code':code,'output_tail':out[-2000:]}


# ---------------- prompts ----------------
LOC_SYS='You locate the code responsible for a reported repository defect. Do not write a patch. Answer with one JSON object only.'
REPRO_SYS='You write a minimal standalone Python reproduction script for a reported defect. Answer with the script only, in one ```python block.'
PATCH_SYS='Repair the reported repository defect using the supplied source evidence. Emit edit_file calls only. The driver executes and grades the calls independently. Do not invent a tool response or answer in prose.'
GENERIC_GUIDE=('Repair guidelines: fix the root cause described by the issue with the smallest change; keep public signatures and unrelated behavior unchanged; '
               'do not special-case the reproduction input; do not add new dependencies; keep the existing code style.')


def loc_prompt(issue,tree,hits,names):
    return (f'Issue:\n{issue}\n\nRepository source files (tests excluded):\n{tree}\n\nDefinitions matching identifiers mentioned in the issue ({", ".join(names[:30])}):\n'+('\n'.join(hits) or '(none found)')+
            '\n\nReply with exactly one JSON object: {"targets": [{"file": "<path from the list>", "symbol": "<function, Class.method, class or module-level variable name defined in that file>", "reason": "<short>"}]} '
            'with 1 to 3 targets, most likely first. Choose the code that must change to fix the issue.')


def repro_prompt(issue,excerpts):
    return (f'Issue:\n{issue}\n\nRelevant source (current, unfixed):\n{excerpts}\n\n'
            'Write a standalone Python script that reproduces the defect through the package\'s public API, run from the repository root with the package installed. '
            'It must exit with status 0 when the defect is FIXED and fail (raise AssertionError or exit non-zero) while the defect is present. '
            'For performance defects, time the operation with time.perf_counter() on an input large enough that the current code clearly exceeds a threshold you choose (keep total runtime under 30 seconds) and assert the time is below it. '
            'Print a short line describing what was observed. No network, no files outside the working directory.')


def patch_prompt(issue,blocks,repro,repro_result):
    ex='\n'.join(f'BEGIN_SOURCE {i+1} ({b["file"]}, {b["symbol"]})\n{b["text"]}END_SOURCE {i+1}' for i,b in enumerate(blocks))
    rp=('' if not repro else f'\n\nHost reproduction script (exit 0 means fixed):\n```python\n{repro}\n```\nIts result on the current code: exit {repro_result["exit_code"]}, output:\n{repro_result["output_tail"][-800:]}')
    return (f'Issue:\n{issue}\n\n{GENERIC_GUIDE}{rp}\n\nExact current source excerpts (edit only inside these):\n{ex}\n\n'
            'Before emitting a call, check internally that old_string occurs verbatim in the excerpt (preserve indentation, quotes, backslashes and newlines). '
            f'Emit one edit_file call per excerpt you change (at most {len(blocks)}), with filepath set to that excerpt\'s file. Do not read files, run commands, explain, or retry.')


def parse_json(text):
    m=re.search(r'\{.*\}',text,re.S)
    if not m:return None
    try:return json.loads(m.group(0))
    except json.JSONDecodeError:return None


def parse_code(text):
    m=re.search(r'```(?:python)?\n(.*?)```',text,re.S);return (m.group(1) if m else text).strip()+'\n'


# ---------------- per task ----------------
def guarded_patch(model,folder,msgs,sources,blocks,temp,seed):
    """sources: {file: text}. Applies calls grouped by file, each restricted to that file's excerpt regions."""
    status=None;log=[]
    for attempt in range(2):
        m=copy.deepcopy(msgs)
        if attempt and status:m[-1]['content']+='\n\nHost notice (not a grader result): '+status['message']
        r=chat(model,m,folder/f'gen{attempt}',1536,temp,None if seed is None else seed+attempt,TOOLS)
        calls=r['calls'];bad=[c for c in calls if c.get('arguments',{}).get('filepath') not in sources]
        if not calls:status={'status':'not_found','message':'Your reply contained no edit_file call. Respond only with edit_file tool calls that change the supplied excerpts; no prose.'}
        elif bad:status={'status':'out_of_region','message':'Edit only the supplied excerpts; filepath must be one of: '+', '.join(sources)}
        else:
            new=dict(sources);status={'status':'ok'}
            for f in sources:
                fc=[c for c in calls if c['arguments'].get('filepath')==f]
                if not fc:continue
                regs=[guard.Region(b['start_marker'],b['end_marker']) for b in blocks if b['file']==f]
                st=guard.check_edits(fc,new[f],f,regs)
                if st['status']!='ok':status=st;break
                new[f]=st['after']
            if status['status']=='ok' and new==sources:status={'status':'noop','message':'Your calls change nothing. Emit edits that change the code.'}
        log.append({'gen':attempt,'status':status['status'],'finish':r['finish_reason'],'n_calls':len(calls)})
        if status['status']=='ok':dump(folder/'guard.json',{'final':'ok','log':log});return new,'ok',len(log)
        if status['status'] not in guard.RETRYABLE:break
    dump(folder/'guard.json',{'final':status['status'],'log':log});return None,status['status'],len(log)


def markers(repo,rel,span):
    """Start marker: shortest prefix of the excerpt (whole lines) that is unique in the file. End: next non-blank line."""
    src=repo.read(rel);lines=src.splitlines(keepends=True);a,b=span;start=None
    for k in range(a-1,b):
        cand=''.join(lines[a-1:k+1])
        if src.count(cand)==1:start=cand;break
    nxt=next((l for l in lines[b:] if l.strip()),None)
    return start,(nxt if nxt else '\n__EOF_NEVER__')


MAX_BLOCK=9000


def solve(model,tid,base,state,save):
    row_task={'task':tid,'samples':[]};tasks={json.loads(l)['instance_id']:json.loads(l) for l in (DATA/'tasks.jsonl').read_text().splitlines()};t=tasks[tid]
    issue=t['problem_statement'][:MAX_ISSUE];repo=Repo(tid);f=base/tid
    hits,names=repo.grep(issue)
    loc=chat(model,[{'role':'system','content':LOC_SYS},{'role':'user','content':loc_prompt(issue,repo.tree(),hits,names)}],f/'localize',768,0)
    targets=(parse_json(loc['content']) or {}).get('targets',[])[:3];blocks=[]
    skipped=[]
    for tg in targets:
        rel=str(tg.get('file','')).strip();sym=str(tg.get('symbol','')).strip()
        if not sym:skipped.append({'target':tg,'why':'no symbol'});continue
        f2,r=repo.locate(rel,sym)
        if not r:skipped.append({'target':tg,'why':'symbol not found in any source file'});continue
        span=r['span'];txt=excerpt_text(repo,f2,span)
        if len(txt)>MAX_BLOCK and r['is_class']:
            init=next((n for n in r['node'].body if getattr(n,'name',None)=='__init__'),None)
            if init:span=(min([init.lineno]+[d.lineno for d in init.decorator_list]),init.end_lineno);txt=excerpt_text(repo,f2,span);sym=sym+'.__init__'
        if len(txt)>MAX_BLOCK:skipped.append({'target':tg,'why':f'excerpt too large ({len(txt)} chars)'});continue
        s,e=markers(repo,f2,span)
        if s is None:skipped.append({'target':tg,'why':'no unique start marker'});continue
        if any(b['file']==f2 and not (span[1]<b['span'][0] or span[0]>b['span'][1]) for b in blocks):skipped.append({'target':tg,'why':'overlaps previous target'});continue
        if sum(len(b['text']) for b in blocks)+len(txt)>MAX_EXCERPTS:skipped.append({'target':tg,'why':'total excerpt budget'});continue
        blocks.append({'file':f2,'symbol':sym,'span':span,'text':txt,'start_marker':s,'end_marker':e,'model_file':rel})
    row_task['skipped_targets']=skipped
    row_task['localized']=[{'file':b['file'],'symbol':b['symbol'],'span':b['span']} for b in blocks];row_task['gold_files']=t['src_files']
    row_task['loc_hit_file']=any(b['file'] in t['src_files'] for b in blocks)
    if not blocks:row_task['status']='localize_failed';repo.tmp.cleanup();return row_task
    box=Box(tid,t['repo'])
    try:
        ex='\n'.join(f'# {b["file"]} :: {b["symbol"]}\n{b["text"]}' for b in blocks)
        repro=None;rr=None;why=''
        for k in range(3):
            msg=repro_prompt(issue,ex)+('' if k==0 else f'\n\nYour previous script is not a valid reproduction: {why}. Output:\n{rr["output_tail"][-600:]}\nWrite a corrected script that fails on the current code because of the defect itself.')
            r=chat(model,[{'role':'system','content':REPRO_SYS},{'role':'user','content':msg}],f/f'repro{k}',1024,0)
            script=parse_code(r['content']);box.reset();rr=run_repro(box,script);ok,why=repro_verdict(rr);rr['valid']=ok;rr['why']=why;dump(f/f'repro{k}/run.json',rr)
            if ok:repro=script;break
        row_task['repro_valid']=repro is not None;row_task['repro_tries']=k+1
        tests=related_tests(repo,[b['file'] for b in blocks]);box.reset();base_t=run_tests(box,tests)
        row_task['tests']=tests;row_task['baseline_test_failures']=len(base_t['failed'])
        sources={b['file']:repo.read(b['file']) for b in blocks};selected=None
        for s in SAMPLES:
            sf=f/'samples'/s['id'];state['current']=f'{tid}/{s["id"]}';save()
            msgs=[{'role':'system','content':PATCH_SYS},{'role':'user','content':patch_prompt(issue,blocks,repro,rr)}]
            new,gs,ng=guarded_patch(model,sf,msgs,sources,blocks,s['temperature'],s.get('seed'));row={'sample':s['id'],'guard':gs,'generations':ng}
            if new is not None:
                box.reset()
                for rel,txt in new.items():box.write(rel,txt)
                patch=box.diff();(sf/'candidate.patch').write_text(patch)
                pr=run_repro(box,repro) if repro else None
                ct=run_tests(box,tests);new_fail=sorted(ct['failed']-base_t['failed'])
                row.update(repro_pass=(pr['exit_code']==0) if pr else None,new_test_failures=len(new_fail),public_pass=bool((pr is None or pr['exit_code']==0) and not new_fail and (ct['exit_code'] in (0,1,5,None))))
                dump(sf/'public.json',{'repro':pr,'tests':{'failed_new':new_fail,'output_tail':ct['output_tail']}})
                g=subprocess.run([sys.executable,str(HERE/'grade.py'),'--task',tid,'--patch',str(sf/'candidate.patch'),'--out',str(sf/'hidden')],capture_output=True,text=True,timeout=1800)
                try:row['hidden_resolved']=json.loads(g.stdout.strip().splitlines()[-1])['resolved']
                except (ValueError,IndexError,KeyError):row['hidden_resolved']=None
            else:row.update(public_pass=False,hidden_resolved=False)
            if selected is None and row['public_pass']:selected=s['id'];row['selected']=True
            row_task['samples'].append(row);dump(f/'task.json',row_task)
        row_task['selected']=selected;row_task['selected_resolved']=next((r['hidden_resolved'] for r in row_task['samples'] if r.get('selected')),None)
        row_task['any_resolved']=any(r.get('hidden_resolved') for r in row_task['samples']);row_task['status']='done'
    finally:box.close();repo.tmp.cleanup()
    return row_task


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['12b','31b']);p.add_argument('--tasks',nargs='+',required=True);p.add_argument('--run',default='generic-v1');p.add_argument('--resume',action='store_true');a=p.parse_args()
    base=ROOT/'runs'/a.run/a.model
    if (base/'state.json').exists() and not a.resume:raise FileExistsError(str(base))
    if a.resume:
        state=json.loads((base/'state.json').read_text());state['results']=[r for r in state['results'] if r.get('status') in ('done','localize_failed')]
        done={r['task'] for r in state['results']};stamp=time.strftime('%Y%m%dT%H%M%S')
        for tid in a.tasks:
            if tid not in done and (base/tid).exists():(base/tid).rename(base/f'{tid}.interrupted-{stamp}')
        state.setdefault('resumes',[]).append({'time':stamp,'kept':sorted(done)});state['status']='running'
    else:
        base.mkdir(parents=True);state={'status':'running','model':a.model,'tasks':a.tasks,'results':[]};done=set()
    def save():dump(base/'state.json',state);report(base,a.run,a.model)
    with (ROOT/'runs/pipeline/shared-worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        dump(base/('frozen-inputs.json' if not a.resume else f'frozen-inputs.resume-{time.strftime("%Y%m%dT%H%M%S")}.json'),{str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),HERE/'grade.py',ROOT/'scripts/harness/edit_guard.py',ROOT/'experiments/methods/31-generic-v1.md']})
        try:
            start(a.model)
            for tid in a.tasks:
                if tid in done:continue
                state['current']=tid;save()
                try:state['results'].append(solve(a.model,tid,base,state,save))
                except Exception as e:state['results'].append({'task':tid,'status':'error','error':repr(e)[:500]})
                save()
            state['status']='complete';state.pop('current',None)
        except Exception as e:state.update(status='needs_review',error=repr(e));raise
        finally:save()


def report(base,run,model):
    out=ROOT/'reports'/run/model;out.mkdir(parents=True,exist_ok=True);st=json.loads((base/'state.json').read_text())
    L=[f'# {run} — {model.upper()}','',f"Trạng thái: `{st.get('status')}`",'','| task | status | loc đúng file | repro hợp lệ | tests | selected | selected resolved | any resolved | samples (guard/public/hidden) |','|---|---|---|---|---|---|---|---|---|']
    for r in st.get('results',[]):
        L.append(f"| {r['task']} | {r.get('status')} | {r.get('loc_hit_file')} | {r.get('repro_valid')} | {len(r.get('tests',[]))} | {r.get('selected')} | {r.get('selected_resolved')} | {r.get('any_resolved')} | "+'; '.join(f"{x['sample']}:{x['guard']}/{x.get('public_pass')}/{x.get('hidden_resolved')}" for x in r.get('samples',[]))+' |')
    (out/'summary.md').write_text('\n'.join(L)+'\n');dump(out/'state.json',st)

if __name__=='__main__':main()
