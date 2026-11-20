#!/bin/bash
# generic_v6: smoke on w3lib_264, then the remaining 7 dev tasks (same output folder; finished tasks are skipped).
cd "$(dirname "$0")/../.."
OUT=runs/official-generic-v6/31b
.venv-official/bin/python scripts/generic/run_official.py --submission submission_candidates/generic_v6/31b --model 31b --tasks w3lib_264 --out $OUT > runs/official-generic-v6-31b.log 2>&1
echo "$(date -u +%FT%TZ) step3f smoke (generic_v6 w3lib_264) exit=$?" >> runs/generic-queue.log
TASKS=$(python3 -c "import json;print(' '.join(json.load(open('experiments/generic_v1/dev-tasks.json'))['ids']))")
.venv-official/bin/python scripts/generic/run_official.py --submission submission_candidates/generic_v6/31b --model 31b --tasks $TASKS --out $OUT >> runs/official-generic-v6-31b.log 2>&1
echo "$(date -u +%FT%TZ) step3f (official generic_v6, 8 tasks) exit=$?" >> runs/generic-queue.log
