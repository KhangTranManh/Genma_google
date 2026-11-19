"""Fixed sandbox operations: bounded inspection and pytest, no arbitrary shell input."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

WORKSPACE=Path('/workspace')
STATE=Path('/tmp/gemma-staged-v1-ops.json')
INSPECTION_LIMIT=8
DUPLICATE_LIMIT=2
READ_CHARS=2400
TEST_LIMIT=4


def valid_path(root,value):
    path=Path(value)
    if path.is_absolute() or '..' in path.parts or '.git' in path.parts:
        raise ValueError('Use a relative workspace path without .git or traversal')
    resolved=(root/path).resolve()
    if not resolved.is_relative_to(root.resolve()):raise ValueError('Path escapes workspace')
    return resolved


def load_state(path):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return {'inspection_calls':0,'test_calls':0,'review_calls':0,'seen':{}}


def save_state(path,state):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state));tmp.replace(path)


def inspect_budget(state,key):
    if state['inspection_calls']>=INSPECTION_LIMIT:
        return {'status':'denied','reason':'inspection_budget_exhausted','next_action':'Use collected evidence to edit, test, or finish this stage with a precise blocker.'}
    if state['seen'].get(key,0)>=DUPLICATE_LIMIT:
        return {'status':'denied','reason':'duplicate_inspection','next_action':'This unchanged request already succeeded twice. Use a different question/range, edit, or finish the stage.'}
    state['inspection_calls']+=1;state['seen'][key]=state['seen'].get(key,0)+1
    return None


def operate(args,root=WORKSPACE,state_path=STATE):
    state=load_state(state_path)
    if args.action=='status':return dict(status='ok',inspection_limit=INSPECTION_LIMIT,test_limit=TEST_LIMIT,**state)
    if args.action=='read':
        p=valid_path(root,args.path)
        if not p.is_file() or p.stat().st_size>1_000_000:raise ValueError('Missing file or file exceeds 1 MB')
        if args.start<1 or args.end<args.start or args.end-args.start>=80:raise ValueError('Choose 1-80 lines with valid bounds')
        text=p.read_text(errors='replace');lines=text.splitlines()
        content='\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines) if args.start<=i+1<=args.end)
        key=json.dumps(['read',str(p.relative_to(root.resolve())),args.start,args.end,hashlib.sha256(content.encode()).hexdigest()])
        denied=inspect_budget(state,key)
        if denied:return denied
        save_state(state_path,state)
        return {'status':'ok','path':args.path,'content':content[:READ_CHARS],
                'truncated':len(content)>READ_CHARS,'range':[args.start,args.end],
                'inspection_remaining':INSPECTION_LIMIT-state['inspection_calls']}
    if args.action=='search':
        folder=valid_path(root,args.path)
        if not folder.is_dir() or not args.needle or len(args.needle)>200:raise ValueError('Search needs a directory and a literal needle <=200 chars')
        # Directory searches share a bounded call allowance; no repository regex execution.
        key=json.dumps(['search',args.path,args.needle])
        denied=inspect_budget(state,key)
        if denied:return denied
        save_state(state_path,state);matches=[];scanned=0
        import os
        for directory,dirs,files in os.walk(folder,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d not in ('.git','.venv','venv','__pycache__','build','dist','node_modules'))
            for name in sorted(files):
                p=Path(directory)/name
                if p.is_symlink() or name.startswith('.adk_exec_'):continue
                scanned+=1
                if scanned>3000:return {'status':'ok','matches':matches,'truncated':True,'reason':'scan_limit'}
                if p.stat().st_size>512_000:continue
                try:lines=p.read_text(errors='strict').splitlines()
                except (UnicodeError,OSError):continue
                for number,line in enumerate(lines,1):
                    if args.needle in line:
                        matches.append({'path':str(p.relative_to(root.resolve())),'line':number,'text':line[:140]})
                        if len(matches)>=12:return {'status':'ok','matches':matches,'truncated':True}
        return {'status':'ok','matches':matches,'truncated':False}
    if args.action=='test':
        path=valid_path(root,args.path)
        if not path.exists() or '.git' in path.parts:raise ValueError('Choose an existing test file/directory')
        if state['test_calls']>=TEST_LIMIT:return {'status':'denied','reason':'test_budget_exhausted','next_action':'Report verification evidence and hand off.'}
        state['test_calls']+=1;save_state(state_path,state)
        with tempfile.TemporaryFile() as output:
            try:
                result=subprocess.run([sys.executable,'-m','pytest',str(path),'-q','--disable-warnings','--maxfail=3'],cwd=root,stdout=output,stderr=subprocess.STDOUT,timeout=45)
                code=result.returncode;timed_out=False
            except subprocess.TimeoutExpired:code=None;timed_out=True
            output.seek(0);text=output.read(2401).decode(errors='replace')
        return {'status':'ok','exit_code':code,'timed_out':timed_out,'output':text[:2400],
                'truncated':len(text)>2400,'test_remaining':TEST_LIMIT-state['test_calls']}
    if args.action=='review':
        if state['review_calls']>=2:return {'status':'denied','reason':'review_budget_exhausted'}
        state['review_calls']+=1;save_state(state_path,state)
        result=subprocess.run(['git','diff','--stat'],cwd=root,text=True,capture_output=True,timeout=5)
        return {'status':'ok','exit_code':result.returncode,'diff_stat':result.stdout[:2400]}
    raise ValueError('Unsupported action')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['status','search','read','test','review'])
    parser.add_argument('--path',default='.');parser.add_argument('--needle',default='')
    parser.add_argument('--start',type=int,default=1);parser.add_argument('--end',type=int,default=80)
    args=parser.parse_args()
    try:result=operate(args)
    except (ValueError,OSError,json.JSONDecodeError,subprocess.SubprocessError) as error:result={'status':'error','message':str(error)}
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
