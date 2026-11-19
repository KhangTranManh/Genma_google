#!/bin/bash
# Sequential GPU queue for the three requested steps. Each step writes its own runs/ folder and a status line.
cd "$(dirname "$0")/../.."
LOG=runs/generic-queue.log; say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }
say "queue started"
while pgrep -f "scripts/generic/run_variance.sh" >/dev/null; do sleep 30; done
say "step1 (variance) finished: $(cat runs/generic-variance.out | tr '\n' ' ')"
while pgrep -f "scripts/generic/prepare_tasks.sh" >/dev/null; do sleep 30; done
USABLE=$(python3 - <<'PY'
import json
from pathlib import Path
new=json.load(open('experiments/generic_v1/dev20-tasks.json'))['new'];ok=[]
for t in new:
    g=Path(f'runs/generic-preflight-v1/{t}/grade.json')
    if g.exists() and json.loads(g.read_text()).get('usable'):ok.append(t)
print(' '.join(ok))
PY
)
say "step2 usable new tasks: $USABLE"
.venv-official/bin/python scripts/generic/pipeline.py --model 31b --evidence --extra-checks --tasks $USABLE --run generic-dev20 > runs/generic-dev20-31b.log 2>&1
say "step2 (dev20 pipeline) exit=$?"
TASKS=$(python3 -c "import json;print(' '.join(json.load(open('experiments/generic_v1/dev-tasks.json'))['ids']))")
.venv-official/bin/python scripts/generic/run_official.py --submission submission_candidates/generic_v1/31b --model 31b --tasks $TASKS --out runs/official-generic-v1/31b > runs/official-generic-v1-31b.log 2>&1
say "step3 (official submission eval) exit=$?"
say "queue done"
