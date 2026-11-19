#!/bin/bash
# Download snapshots/locks, build images and run the official preflight for the given tasks. CPU/docker only.
cd "$(dirname "$0")/../.."
python3 - "$@" <<'PY'
import json,sys,urllib.request,urllib.parse,shutil
from pathlib import Path
root=Path('data/freshswe');tasks={json.loads(l)['instance_id']:json.loads(l) for l in (root/'tasks.jsonl').read_text().splitlines()}
base='https://www.kaggle.com/api/v1/datasets/download/moshegolderson/freshswe-py/'
for i in sys.argv[1:]:
    for name in [f'snapshots/{i}.tgz',f'locks/{tasks[i]["base_commit"]}.txt']:
        p=root/name
        if not p.exists():
            with urllib.request.urlopen(base+urllib.parse.quote(name,safe=''),timeout=180) as r,p.open('wb') as o:shutil.copyfileobj(r,o)
PY
for t in "$@"; do
  python3 scripts/b4/prepare.py "$t" > /dev/null 2>runs/official-build-$t.err && echo "$t image ok" || { echo "$t image FAILED"; continue; }
  timeout 1800 .venv-official/bin/python scripts/generic/grade.py --task "$t" --preflight --out runs/generic-preflight-v1/$t 2>/dev/null | tail -1 | python3 -c "import json,sys
try:
  d=json.loads(sys.stdin.read());print(d['task'],'usable',d['usable'],'base',d['baseline']['resolved'],d['baseline']['error'],'gold',d['gold']['resolved'],d['gold']['error'])
except Exception as e:print('$t preflight ERROR',e)"
done
