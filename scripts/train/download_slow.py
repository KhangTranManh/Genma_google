"""Sequential snapshot download with spacing and 429 backoff."""
import json,sys,time,urllib.request,urllib.parse,urllib.error,shutil
from pathlib import Path
root=Path('data/freshswe');ids=json.load(open(sys.argv[1]))['ids'];base='https://www.kaggle.com/api/v1/datasets/download/moshegolderson/freshswe-py/'
todo=[i for i in ids if not (root/'snapshots'/f'{i}.tgz').exists()];print('todo',len(todo),flush=True);ok=0
for i in todo:
    for attempt in range(6):
        try:
            with urllib.request.urlopen(base+urllib.parse.quote(f'snapshots/{i}.tgz',safe=''),timeout=180) as r,open(root/'snapshots'/f'{i}.tgz.part','wb') as o:shutil.copyfileobj(r,o)
            (root/'snapshots'/f'{i}.tgz.part').rename(root/'snapshots'/f'{i}.tgz');ok+=1;break
        except urllib.error.HTTPError as e:
            if e.code==429:time.sleep(60*(attempt+1));continue
            print('fail',i,e.code,flush=True);break
        except Exception as e:print('fail',i,type(e).__name__,flush=True);time.sleep(10)
    time.sleep(5)
print('done ok',ok,'of',len(todo),flush=True)
