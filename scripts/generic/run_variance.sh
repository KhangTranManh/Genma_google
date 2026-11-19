#!/bin/bash
# Step 1: two repeat runs of the v5 configuration on the 8 dev tasks (sequential; shared GPU lock).
cd "$(dirname "$0")/../.."
TASKS=$(python3 -c "import json;print(' '.join(json.load(open('experiments/generic_v1/dev-tasks.json'))['ids']))")
for r in rep1 rep2; do
  .venv-official/bin/python scripts/generic/pipeline.py --model 31b --evidence --extra-checks --tasks $TASKS --run generic-$r > runs/generic-$r-31b.log 2>&1
  echo "generic-$r exit=$?"
done
