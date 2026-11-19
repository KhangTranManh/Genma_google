"""Extract original source, upstream reference (gold patch applied) and upstream test patch per B4 task."""
from pathlib import Path
import json,subprocess,tarfile,tempfile
import os
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/os.environ.get('B4_EXP','experiments/b4_v1')

def main():
    tasks=json.loads((EXP/'tasks.json').read_text());rows={json.loads(l)['instance_id']:json.loads(l) for l in (ROOT/'data/freshswe/tasks.jsonl').read_text().splitlines()}
    for tid,spec in tasks.items():
        out=EXP/tid;out.mkdir(exist_ok=True);row=rows[tid]
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(ROOT/'data/freshswe/snapshots'/f'{tid}.tgz') as tf:tf.extractall(tmp,filter='data')
            (out/'original.py').write_text((Path(tmp)/spec['file']).read_text())
            (out/'gold.patch').write_text(row['patch']);(out/'test.patch').write_text(row['test_patch'])
            subprocess.run(['git','apply','--include',spec['file'],str(out/'gold.patch')],cwd=tmp,check=True)
            (out/'reference.py').write_text((Path(tmp)/spec['file']).read_text())
        src=(out/'original.py').read_text()
        for a,b in spec['regions']:
            i=src.find(a);j=src.find(b,i+1);assert i>=0 and j>i,(tid,a)
        print(tid,'regions ok',len(spec['regions']),'reference differs',(out/'reference.py').read_text()!=src)

if __name__=='__main__':main()
