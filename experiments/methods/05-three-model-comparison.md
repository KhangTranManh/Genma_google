# Matched task and inference criteria for all three models

The current 31B/12B completion queue and a separate E4B control use identical task
settings: 900 seconds, 48 turns, 96 tool calls, one fixed tool-recovery prompt,
unchanged agent workflow, the same synthetic issue and the same independent tests.
Queue identity and model order differ; the comparison generator checks the actual
prompt/code/data/serving/task-budget protocol rather than assuming a match.

The E4B control extends the same configuration instead of modifying the already
running 31B/12B experiment. Earlier failures and the 240-second runs remain separate.
A failure or exhausted budget is a result, not a successful completion.

After the task queues finish, a dedicated performance timer measures each model
without concurrent task inference. Each model gets one warm-up plus three 128-token
streaming requests with identical text, temperature zero, and thinking disabled.
Record median end-to-end throughput, median time to first text chunk and sampled
VRAM per GPU. These measurements are a short benchmark, not peak task VRAM or
throughput on long repositories.

The automatic table includes patch submission, public and independent tests,
wall-clock task time, turns/tool calls, input/output tokens, rejected file edits,
throughput, TTFT and VRAM. Preserve raw manifests, trajectories, benchmark trials
and GPU samples. Missing evidence stays missing; do not substitute historical scores
or infer unmeasured values.

Outputs:

- `reports/model-comparison.md`
- `reports/model-comparison.csv`
- `reports/model-comparison.json`
- `runs/pipeline/model_metrics_v1/MODEL.json`

A single synthetic issue checks the harness but is insufficient to rank models for
general software engineering. No hand-written task solution is fed to an agent.
