# Bounded triggers and self-improvement

The original combined queue is now historical (`legacy_mixed`) and stopped at
needs_review after a 31B run timeout. New methods are defined independently under
`configs/experiments/`; see [experiment workflow](../experiments/README.md).
The enabled timer now selects only `model_sweep_v1`; legacy state is retained unchanged.
Prompt-only and workflow-code experiments remain inactive. Select a profile with
`python scripts/install_triggers.py --experiment model_sweep` (or `prompt_only`).

The systemd timer invokes one pipeline action per activation. It first fires after
2 minutes, then 5 minutes after the preceding worker finishes. systemd serializes
the service and an additional file lock rejects overlapping manual invocations.
This is a finite experiment queue, not continuous inference or a monitoring daemon.

The configured model order is E4B -> 12B -> 31B. Checkpoints are public upstream
Google compressed-tensors releases pinned by revision in `configs/project.toml`.
Downloads validate file sizes; vLLM startup is checked against the served model alias.
The two-GPU serving settings apply to every stage. Memory fitness and throughput
for larger models remain unverified until those stages actually run.

Each model runs the synthetic issue. If it fails or exhausts its budget, the same
model may propose one new general system prompt from its own agent-visible
trajectory. The candidate is versioned and tried on the next run. Only a locally
passing candidate is retained for the following stages. A failure after the allowed
trial is recorded and the queue proceeds to the next model; infrastructure/startup
errors stop the queue for review and attempt to restore the last working model.
A passing toy issue is a workflow smoke result, not evidence of general improvement.

Candidate prompt generation never reads the independent evaluator, reference
solutions, or evaluation output. It can see its own tool calls, command errors,
issue text and termination reason. It has no host-editing tools. Host code validates
the JSON and stores the proposed prompt under `runs/prompt-versions/`.
`submission/prompts/system.md` is not overwritten automatically.

## Run and inspect

```bash
./gemma-lab improve-prompt --model e4b --from-run runs/RUN_ID --evaluate-demo
./gemma-lab demo --model e4b --prompt runs/prompt-versions/VERSION/system.md
.venv/bin/python scripts/install_triggers.py
.venv/bin/python -m gemma_lab.worker --status
systemctl list-timers gemma-lab-worker.timer --no-pager
systemctl status gemma-lab-worker.service --no-pager
```

The state is `runs/pipeline/state.json`; the worker log is
`runs/pipeline/worker.log`. Model server logs are `runs/vllm-12b.log`, etc.
The server is supervised separately so it remains available between triggered jobs.
The installed worker stops its timer when the queue reaches `complete` or
`needs_review`. Stop the timer manually when desired:

```bash
systemctl stop gemma-lab-worker.timer
```

To pause a currently running job as well, stop `gemma-lab-worker.service`. An
interrupted job leaves an in-progress marker; the next activation stops for review.
Inspect its artifacts before manually adjusting the state. Starting a job immediately
uses `systemctl start --no-block gemma-lab-worker.service`.

Official competition harness integration is still pending. These triggers execute
local synthetic tests only; no Kaggle submission, external messaging or publishing occurs.
