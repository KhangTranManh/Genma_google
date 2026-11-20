"""Build SFT examples from public FreshSWE gold patches (dev tasks excluded).

Each example: system + user (verbatim issue, current source excerpts of the functions the fix touches, edit
instructions) -> assistant edit_file tool call(s) whose old_string is the SHORTEST fragment unique in the
current file. Applying the calls in order to the original file must reproduce the gold file exactly,
otherwise the task is skipped. Rendered with the model's own chat template (native tool-call format).
  .venv-train/bin/python scripts/train/build_dataset.py experiments/train_v1/train-tasks.json data/train_v1
"""
import ast,difflib,json,re,subprocess,sys,tarfile,tempfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/freshswe'
TOOLS=json.loads((ROOT/'experiments/b4_v1/tools.json').read_text())
SYSTEM='Repair the reported repository defect using the supplied source evidence. Emit edit_file calls only. The driver executes and grades the calls independently. Do not invent a tool response or answer in prose.'
GUIDE=('Repair guidelines: fix the root cause described by the issue with the smallest change; keep public signatures and unrelated behavior unchanged; '
       'do not special-case the reproduction input; do not add new dependencies; keep the existing code style.')
EDIT_RULE=('Use the SHORTEST old_string that is unique in the file and contains the characters you change (usually part of one line). '
           'Copy it exactly from the excerpt. Emit one edit_file call per change, with filepath set to the excerpt\'s file. Do not explain.')
MAX_ISSUE=6000;MIN_FRAG=6


def enclosing(src,line):
    """(start,end) of the innermost def/class containing line, else a +-12 line window."""
    try:tree=ast.parse(src)
    except SyntaxError:tree=None
    best=None
    if tree:
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                s=min([n.lineno]+[d.lineno for d in n.decorator_list]);e=n.end_lineno
                if s<=line<=e and (best is None or e-s<best[1]-best[0]):best=(s,e)
    if best and best[1]-best[0]<=150:return best
    return max(1,line-12),line+12


def shortest_unique(cur,old,new,start):
    """Given that cur[start:start+len(old)] == old must become new, return (frag_old,frag_new) minimal & unique."""
    p=0
    while p<min(len(old),len(new)) and old[p]==new[p]:p+=1
    q=0
    while q<min(len(old),len(new))-p and old[len(old)-1-q]==new[len(new)-1-q]:q+=1
    a=start+p;b=start+len(old)-q;na=new[p:len(new)-q]   # cur[a:b] -> na
    def ok(i,j):
        frag=cur[i:j]
        return len(frag)>=MIN_FRAG and frag.count('\n')<=40 and cur.count(frag)==1
    i,j=a,b
    while not ok(i,j):
        if i==0 and j==len(cur):return None
        # grow to the next word boundary on both sides
        i=max(0,i-1);j=min(len(cur),j+1)
        while i>0 and cur[i-1].isalnum():i-=1
        while j<len(cur) and cur[j].isalnum():j+=1
    return cur[i:j],cur[i:a]+na+cur[b:j]


def edits_for(orig,gold):
    """Sequence of (old,new) fragment edits transforming orig into gold, applied in order."""
    a=orig.splitlines(keepends=True);b=gold.splitlines(keepends=True);cur=orig;calls=[];offset=0
    sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':continue
        old=''.join(a[i1:i2]);new=''.join(b[j1:j2]);pos=sum(len(x) for x in a[:i1])+offset
        if not old:  # pure insertion: anchor on the previous line (or the next one at file start)
            if i1>0:prev=a[i1-1];pos-=len(prev);old=prev;new=prev+new
            else:nxt=a[i2] if i2<len(a) else '';old=nxt;new=new+nxt
        assert cur[pos:pos+len(old)]==old
        r=shortest_unique(cur,old,new,pos)
        if r is None:return None
        fo,fn=r;cur=cur.replace(fo,fn,1);calls.append((fo,fn));offset+=len(new)-len(old)
    return calls if cur==gold else None


def build(tid,row,tok):
    files=row['src_files']
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(DATA/'snapshots'/f'{tid}.tgz') as tf:tf.extractall(tmp,filter='data')
        orig={f:(Path(tmp)/f).read_text() for f in files if (Path(tmp)/f).exists()}
        if len(orig)!=len(files):return None,'missing source file'
        r=subprocess.run(['git','apply']+sum([['--include',f] for f in files],[])+['-'],input=row['patch'],text=True,cwd=tmp,capture_output=True)
        if r.returncode:return None,'gold patch does not apply'
        gold={f:(Path(tmp)/f).read_text() for f in files}
    calls=[];spans=[]
    for f in files:
        if orig[f]==gold[f]:continue
        e=edits_for(orig[f],gold[f])
        if e is None:return None,'no unique fragment edit sequence'
        calls+=[{'name':'edit_file','arguments':{'filepath':f,'old_string':o,'new_string':n}} for o,n in e]
        changed=[i+1 for t,i1,i2,_,_ in difflib.SequenceMatcher(None,orig[f].splitlines(),gold[f].splitlines(),autojunk=False).get_opcodes() if t!='equal' for i in range(i1,max(i2,i1+1))]
        for ln in sorted(set(enclosing(orig[f],l) for l in changed)):spans.append((f,ln))
    if not calls:return None,'no source change'
    blocks=[];seen=set()
    for f,(s,e) in spans:
        if (f,s,e) in seen:continue
        seen.add((f,s,e));lines=orig[f].splitlines(keepends=True);blocks.append(f'BEGIN_SOURCE {len(blocks)+1} ({f}, lines {s}-{e})\n'+''.join(lines[s-1:e])+f'END_SOURCE {len(blocks)+1}')
    user=(f"Issue:\n{row['problem_statement'][:MAX_ISSUE]}\n\n{GUIDE}\n\nExact current source excerpts (edit only inside these):\n"+'\n'.join(blocks)+'\n\n'+EDIT_RULE)
    msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':user}]
    # Inference format (vLLM, enable_thinking=False): the generation prompt ends with an empty thought channel and the
    # model then emits `<|tool_call>call:...<tool_call|>` and stops at `<|tool_response>` (verified on raw captures).
    prompt=tok.apply_chat_template(msgs,tools=TOOLS,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    full=tok.apply_chat_template(msgs+[{'role':'assistant','content':'','tool_calls':[{'type':'function','function':c} for c in calls]}],tools=TOOLS,tokenize=False,enable_thinking=False)
    mark='<|turn>model\n';completion=full[full.rindex(mark)+len(mark):]
    if not (completion.startswith('<|tool_call>') and completion.endswith('<|tool_response>')):return None,'unexpected completion format'
    n_prompt=len(tok(prompt,add_special_tokens=False).input_ids);n_comp=len(tok(completion,add_special_tokens=False).input_ids)
    return {'task':tid,'repo':row['repo'],'prompt':prompt,'completion':completion,'n_prompt':n_prompt,'n_completion':n_comp,'n_calls':len(calls)},'ok'


def main():
    from transformers import AutoTokenizer
    ids=json.load(open(sys.argv[1]))['ids'];out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
    tok=AutoTokenizer.from_pretrained(ROOT/'models/gemma-4-12b-it-qat-w4a16-ct')
    rows={json.loads(l)['instance_id']:json.loads(l) for l in (DATA/'tasks.jsonl').read_text().splitlines()};stats=Counter();ex=[]
    for tid in ids:
        if not (DATA/'snapshots'/f'{tid}.tgz').exists():stats['no snapshot']+=1;continue
        try:e,why=build(tid,rows[tid],tok)
        except Exception as err:e,why=None,'error '+type(err).__name__
        stats[why]+=1
        if e:ex.append(e)
    with open(out/'train.jsonl','w') as f:
        for e in ex:f.write(json.dumps(e,ensure_ascii=False)+'\n')
    tot=[e['n_prompt']+e['n_completion'] for e in ex]
    summary={'examples':len(ex),'stats':dict(stats),'tokens_total_median':sorted(tot)[len(tot)//2] if tot else None,'tokens_max':max(tot) if tot else None,
             'over_8k':sum(t>8192 for t in tot),'repos':len({e['repo'] for e in ex}),'calls_per_example':dict(Counter(e['n_calls'] for e in ex))}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
