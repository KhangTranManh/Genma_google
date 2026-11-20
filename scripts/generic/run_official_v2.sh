#!/bin/bash
cd "$(dirname "$0")/../.."
TASKS=$(python3 -c "import json;print(' '.join(json.load(open('experiments/generic_v1/dev-tasks.json'))['ids']))")
.venv-official/bin/python scripts/generic/run_official.py --submission submission_candidates/generic_v2/31b --model 31b --tasks $TASKS --out runs/official-generic-v2/31b > runs/official-generic-v2-31b.log 2>&1
echo "$(date -u +%FT%TZ) step3b (official generic_v2) exit=$?" >> runs/generic-queue.log
