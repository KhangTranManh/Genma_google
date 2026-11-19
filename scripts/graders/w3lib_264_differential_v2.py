"""Container-side differential oracle for w3lib_264 (get_base_url), corpus v2.

v2 adds every printable ASCII character inside quoted attribute values (one fixed case per character,
both quote styles) and a wider random alphabet, after v1 missed '[' (B3 12B sample).

Compares the candidate w3lib.html.get_base_url with the ORIGINAL implementation (and, in hidden
mode, with the upstream REFERENCE fix) on a deterministic corpus of valid and near-valid HTML.

Modes (both reported every run):
  public  - every 'plain' case (well-formed tag, no '<' or '>' inside attribute values) must equal
            the original output. Uses no reference solution, so a harness may use it.
  hidden  - every case must equal the original OR the reference output. Grader only.

Usage inside the container (repo root):
  python w3lib_264_differential.py --orig /tmp/_orig_html.py [--ref /tmp/_ref_html.py]
"""
import argparse,importlib.util,json,random,sys,time

PUNCT='!#$%&()*+,;?@[]\\^`{|}~'
NAMES=['target','id','class','data-x','data-href','xhref','title']
URLS=['https://example.org/path/','/assets/','relative/dir/','http://example.com','https://example.org/a b/','../up/']


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def value(rng,length,risky):
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789/.:-_= '+PUNCT+'\t\n'
    s=''.join(rng.choice(alphabet) for _ in range(length))
    if risky and length:
        i=rng.randrange(length+1);s=s[:i]+rng.choice(['<','>','<b>','a<b'])+s[i:]
    return s


def attr(rng,risky):
    name=rng.choice(NAMES);q=rng.choice(['"',"'",'']);v=value(rng,rng.choice([0,3,20,200,1000]),risky and q!='')
    if q=='':v=''.join(ch for ch in v if ch not in ' \t\n=`<>"\'') or 'v'
    return f'{name}={q}{v}{q}'


def base_tag(rng,risky=False,closed=True,with_href=True):
    pre=[attr(rng,risky) for _ in range(rng.choice([0,0,1,2,3]))];post=[attr(rng,risky) for _ in range(rng.choice([0,1,2]))]
    q=rng.choice(['"',"'"]);eq=rng.choice(['=',' = ','= ',' ='])
    href=f'{rng.choice(["href","HREF","Href"])}{eq}{q}{rng.choice(["",""," "])}{rng.choice(URLS).replace(" ","%20")}{rng.choice(["",""," "])}{q}'
    parts=pre+([href] if with_href else [])+post
    sep=lambda:rng.choice([' ',' ','\n','\t','  '])
    inner=''.join(sep()+p for p in parts)
    end=rng.choice(['>','>',' >','/>',' />']) if closed else ''
    return '<'+rng.choice(['base','BASE','Base'])+(inner if inner else sep())+end


def corpus(seed=264,n=1500):
    rng=random.Random(seed);cases=[]
    fixed=[
        ('<base href="https://example.org/path/">',True),
        ('<base target="_top">see href="http://x.example/" in text',True),
        ('<base target=_top> href="http://y.example/"<p>',True),
        ('<base data-href="http://first/" href="http://second/">',True),
        ('<base xhref="http://first/" href="http://second/">',True),
        ('<base data-extra="'+'x'*1000+'" href="https://example.org/path/">',True),
        ('<html><head><base href="/a/"><base href="/b/"></head>',True),
        ('<base target=_blank><a href="http://link/">x</a>',True),
        ('<!-- <base href="https://bad.example/"> --><p>x</p>',True),
        ('<basefont href="http://no/">',True),
        ('<base\nhref\n=\n"http://nl/"\n>',True),
        ('<base data-x="a<b" href="http://lt/">',False),
        ('<base data-x="a>b" href="http://gt/">',False),
        ('<base target=_top <p href="http://unclosed/">',False),
        ('<base <base href="http://repeat/">',False),
    ]
    import string
    for ch in string.printable.strip()+' \t\n':
        for q in ['"',"'"]:
            if ch==q:continue
            fixed.append((f'<base data-x={q}a{ch}b{q} href="http://p.example/">',ch not in '<>'))
            fixed.append((f'<base title={q}{ch}{q} href="http://q.example/" target=_top>',ch not in '<>'))
    for text,plain in fixed:cases.append({'text':text,'baseurl':'','plain':plain,'kind':'fixed'})
    for i in range(n):
        k=rng.random();risky=k<0.15;closed=not (0.15<=k<0.22)
        tags=[base_tag(rng,risky=risky,closed=closed,with_href=rng.random()>0.1)]
        if rng.random()<0.3:tags.insert(0,base_tag(rng,with_href=False))
        filler=['<html><head>','<title>t</title>','<meta charset="utf-8">','<p>text href="http://text/" more</p>','<a href="http://anchor/">a</a>','<!-- c -->','plain words ']
        doc=''.join(rng.choice(filler) for _ in range(rng.choice([0,1,2])))+''.join(tags)+''.join(rng.choice(filler) for _ in range(rng.choice([0,1,2,3])))
        cases.append({'text':doc,'baseurl':rng.choice(['','https://example.org/root/']),'plain':not risky and closed,'kind':'generated'})
    return cases


def call(fn,case):
    try:return {'ok':fn(case['text'],case['baseurl'])}
    except Exception as e:return {'error':type(e).__name__}


def main():
    p=argparse.ArgumentParser();p.add_argument('--orig',required=True);p.add_argument('--ref');a=p.parse_args()
    sys.path.insert(0,'.')
    import w3lib.html as cand
    orig=load(a.orig,'_orig_html');ref=load(a.ref,'_ref_html') if a.ref else None
    cases=corpus();pub_bad=[];hid_bad=[];slow=[];start=time.perf_counter()
    for i,c in enumerate(cases):
        t=time.perf_counter();got=call(cand.get_base_url,c);dt=time.perf_counter()-t
        if dt>0.5:slow.append({'index':i,'seconds':round(dt,3)})
        want=call(orig.get_base_url,c)
        if c['plain'] and got!=want:pub_bad.append({'index':i,'text':c['text'][:300],'baseurl':c['baseurl'],'original':want,'candidate':got})
        if ref is not None:
            alt=call(ref.get_base_url,c)
            if got!=want and got!=alt:hid_bad.append({'index':i,'plain':c['plain'],'text':c['text'][:300],'baseurl':c['baseurl'],'original':want,'reference':alt,'candidate':got})
    out={'corpus_version':'v2','corpus_seed':264,'n_cases':len(cases),'n_plain':sum(c['plain'] for c in cases),'seconds':round(time.perf_counter()-start,3),
         'public':{'disagreements':len(pub_bad),'examples':pub_bad[:5],'passed':not pub_bad and not slow},
         'slow_cases':slow[:5],'n_slow':len(slow)}
    if ref is not None:out['hidden']={'disagreements':len(hid_bad),'examples':hid_bad[:5],'passed':not hid_bad and not slow}
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
