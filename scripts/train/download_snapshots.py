import json,sys,urllib.request,urllib.parse,shutil,concurrent.futures as cf
from pathlib import Path
root=Path('data/freshswe');ids=json.load(open(sys.argv[1]))['ids'];base='https://www.kaggle.com/api/v1/datasets/download/moshegolderson/freshswe-py/'
def get(i):
    p=root/'snapshots'/f'{i}.tgz'
    if p.exists():return 'have'
    try:
        with urllib.request.urlopen(base+urllib.parse.quote(f'snapshots/{i}.tgz',safe=''),timeout=180) as r,open(str(p)+'.part','wb') as o:shutil.copyfileobj(r,o)
        Path(str(p)+'.part').rename(p);return 'ok'
    except Exception as e:return 'fail '+type(e).__name__
with cf.ThreadPoolExecutor(2) as ex:res=list(ex.map(get,ids))
from collections import Counter;print(Counter(r.split()[0] for r in res))
