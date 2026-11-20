#!/bin/bash
# Train LoRA v1 on 12B and evaluate 12B base vs 12B+LoRA with the generic pipeline (dev8). Each stage logs to runs/train/queue.log.
cd "$(dirname "$0")/../.."
LOG=runs/train/queue.log; say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }
say "queue started"
while [ -n "$(ps -eo args | awk '$2 ~ /download_slow\.py$/')" ]; do sleep 30; done
say "downloads finished: $(ls data/freshswe/snapshots/*.tgz | wc -l) snapshots"
.venv-train/bin/python scripts/train/build_dataset.py experiments/train_v1/train-tasks.json data/train_v1 > runs/train/build.log 2>&1; say "dataset built: $(python3 -c "import json;d=json.load(open('data/train_v1/summary.json'));print(d['examples'],'examples',d['repos'],'repos')")"
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True .venv-train/bin/python scripts/train/train_lora.py --data data/train_v1/train.jsonl --out runs/train/lora_v1 --epochs 1 > runs/train/lora_v1.log 2>&1
say "training exit=$? last: $(tail -1 runs/train/lora_v1/log.jsonl)"
CUDA_VISIBLE_DEVICES=0,1 setsid .venv/bin/vllm serve models/gemma-4-12b-it-qat-w4a16-ct --served-model-name gemma-4-12b-it-qat-w4a16-ct --host 127.0.0.1 --port 8000 --tensor-parallel-size 2 --max-model-len 16384 --gpu-memory-utilization 0.9 --dtype auto --language-model-only --max-num-seqs 2 --max-num-batched-tokens 512 --enable-auto-tool-choice --tool-call-parser gemma4 --reasoning-parser gemma4 --enable-lora --max-lora-rank 16 --max-loras 1 --lora-modules repair_lora_v1=runs/train/lora_v1/adapter > runs/train/vllm-lora-v1.log 2>&1 < /dev/null &
VPID=$!
until curl -s -m 3 127.0.0.1:8000/v1/models | grep -q repair_lora_v1; do sleep 10; done; say "vllm with adapter ready (pid $VPID)"
TASKS=$(python3 -c "import json;print(' '.join(json.load(open('experiments/generic_v1/dev-tasks.json'))['ids']))")
.venv-official/bin/python scripts/generic/pipeline.py --model 12b --no-start --served-name repair_lora_v1 --evidence --extra-checks --tasks $TASKS --run generic-12b-lora-v1 > runs/generic-12b-lora-v1.log 2>&1; say "eval 12B+LoRA exit=$?"
.venv-official/bin/python scripts/generic/pipeline.py --model 12b --no-start --served-name gemma-4-12b-it-qat-w4a16-ct --evidence --extra-checks --tasks $TASKS --run generic-12b-base > runs/generic-12b-base.log 2>&1; say "eval 12B base exit=$?"
kill $VPID; say "queue done"
