"""Host-side runner for the w3lib_264 differential oracle (run with .venv-official).

  --preflight : validate the oracle on original, upstream reference and known-bad variants.
  --audit     : re-grade every stored historical candidate; writes a separate audit, never edits old results.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/infer_edit'))
from grading import setup,dump
from swegemma.sandbox import ContainerManager,ContainerConfig
CHECKERS={'v1':ROOT/'scripts/graders/w3lib_264_differential.py','v2':ROOT/'scripts/graders/w3lib_264_differential_v2.py'}
CHECKER=CHECKERS['v1']
ORIGINAL=(ROOT/'experiments/hint_ladder_v2/source.txt').read_text()
OUT=ROOT/'reports/differential-audit-v1'


def use(version):
    global CHECKER,OUT
    CHECKER=CHECKERS[version];OUT=ROOT/('reports/differential-audit-'+version)


def variant(old,new):
    a=ORIGINAL.index('_baseurl_re =');b=ORIGINAL.index('_meta_refresh_re',a)
    assert old in ORIGINAL[a:b]
    return ORIGINAL[:a]+ORIGINAL[a:b].replace(old,new,1)+ORIGINAL[b:]


REFERENCE=variant('[^>]*','[^<>]*')


def check(manager,cid,source,with_ref=True):
    sb=manager.get_sandbox(cid)
    sb.write_file('w3lib/html.py',source);sb.write_file('_orig_html.py',ORIGINAL);sb.write_file('_ref_html.py',REFERENCE)
    manager.copy_to(cid,CHECKER,'/tmp')
    r=manager.exec(cid,'timeout 300s python /tmp/'+CHECKER.name+' --orig _orig_html.py'+(' --ref _ref_html.py' if with_ref else ''))
    try:return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):return {'error':(r.stderr+r.stdout)[-2000:],'public':{'passed':False},'hidden':{'passed':False}}


def preflight():
    OUT.mkdir(parents=True,exist_ok=True)
    variants={'original':(ORIGINAL,True,True),'reference':(REFERENCE,True,True),
              'exclude_lt_lazy':(variant('[^>]*','[^<]*?'),False,False),'exclude_lt':(variant('[^>]*','[^<]*'),False,False),
              'exclude_space':(variant('[^>]*','[^> <]*'),False,False),'lazy':(variant('[^>]*','[^>]*?'),None,None),
              'bounded100':(variant('[^>]*','[^>]{0,100}?'),False,False),
              'exclude_bracket':(variant('[^>]*','[^>\\[<]*'),False,False),'exclude_newline':(variant('[^>]*','[^<>\\r\\n]*'),False,False)}
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));results={}
    try:
        cid=setup(manager)
        for name,(src,want_pub,want_hid) in variants.items():
            r=check(manager,cid,src);results[name]={'expected_public':want_pub,'expected_hidden':want_hid,'result':r}
            print(name,'public',r.get('public',{}).get('passed'),r.get('public',{}).get('disagreements'),'hidden',r.get('hidden',{}).get('passed'),r.get('hidden',{}).get('disagreements'),flush=True)
    finally:manager.cleanup_all()
    usable=all((v['expected_public'] is None or v['result']['public']['passed']==v['expected_public']) and (v['expected_hidden'] is None or v['result']['hidden']['passed']==v['expected_hidden']) for v in results.values())
    dump(OUT/'preflight.json',{'usable':usable,'checker_sha256':hashlib.sha256(CHECKER.read_bytes()).hexdigest(),'note':'lazy expectation left open (None): recorded, not required','results':results})
    print('usable',usable);return usable


def collect():
    """Return {sha: {'source':..., 'origins':[...]}} for every stored candidate."""
    found={}
    def add(src,origin):
        h=hashlib.sha256(src.encode()).hexdigest();found.setdefault(h,{'source':src,'origins':[]})['origins'].append(origin)
    runs=ROOT/'runs'
    for f in sorted(list(runs.glob('*/**/after-source.txt'))+list(runs.glob('*/**/candidate-source.txt'))):
        if 'preflight' in f.parts:continue
        add(f.read_text(),str(f.relative_to(ROOT)))
    with tempfile.TemporaryDirectory() as tmp:
        for f in sorted(runs.glob('*/**/*.patch')):
            if (f.parent/'after-source.txt').exists() or 'preflight' in f.parts:continue
            text=f.read_text()
            if not text.strip() or 'w3lib/html.py' not in text:continue
            text=''.join('diff --git'+part for part in text.split('diff --git')[1:] if part.split('\n',1)[0].strip().endswith('b/w3lib/html.py'))
            if not text:continue
            work=Path(tmp)/'html.py';work.write_text(ORIGINAL)
            p=subprocess.run(['patch','-s','-o',str(Path(tmp)/'out.py'),str(work)],input=text,text=True,capture_output=True)
            if p.returncode==0:add((Path(tmp)/'out.py').read_text(),str(f.relative_to(ROOT)))
            else:found.setdefault('unapplied',{'source':None,'origins':[]})['origins'].append(str(f.relative_to(ROOT)))
    return found


def audit():
    found=collect();unapplied=found.pop('unapplied',{'origins':[]})['origins']
    manager=ContainerManager(ContainerConfig(image='gemma-official-pilot:w3lib_264'));rows=[]
    try:
        cid=setup(manager)
        for h,item in found.items():
            src=item['source'];a=src.find('_baseurl_re =');b=src.find('_meta_refresh_re',max(a,0))
            r=check(manager,cid,src)
            rows.append({'sha256':h,'baseurl_block':src[a:b].strip() if a>=0 and b>a else None,'is_original':src==ORIGINAL,'public_pass':r.get('public',{}).get('passed'),'hidden_pass':r.get('hidden',{}).get('passed'),
                         'public_disagreements':r.get('public',{}).get('disagreements'),'hidden_disagreements':r.get('hidden',{}).get('disagreements'),'first_hidden_example':(r.get('hidden',{}).get('examples') or [None])[0],'n_origins':len(item['origins']),'origins':item['origins']})
            print(rows[-1]['public_pass'],rows[-1]['hidden_pass'],len(item['origins']),(rows[-1]['baseurl_block'] or '')[:80].replace('\n',' '),flush=True)
    finally:manager.cleanup_all()
    dump(OUT/'audit.json',{'status':'post_hoc_audit','modifies_old_results':False,'checker_sha256':hashlib.sha256(CHECKER.read_bytes()).hexdigest(),'n_unique_sources':len(rows),'unapplied_patches':unapplied,'rows':rows})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='v1',choices=['v1','v2']);p.add_argument('--preflight',action='store_true');p.add_argument('--audit',action='store_true');a=p.parse_args();use(a.version)
    if a.preflight:raise SystemExit(0 if preflight() else 2)
    if a.audit:audit()
