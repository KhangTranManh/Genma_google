# Follow-up — 31B completion with a matched 12B control

The original 31B trial ran out of its 240-second budget after repeatedly submitting
an over-escaped whole-function edit that did not match the source. The next trial
addresses completion with a general tool-recovery prompt and a larger budget.

Run 31B first, then 12B, with exactly the same prompt, workflow, synthetic issue,
serving parameters and limits: 900 seconds, 48 model turns and 96 tool calls.
Do not change source or prompt while this experiment is active. There is no prompt
optimizer or workflow-code mutation in this queue.

This is a separate experiment: `model_31b_retry_v1`. The prompt and budgets differ
from the initial model sweep, so do not attribute a difference versus the old 31B
run solely to model size or time. The matched 12B trial provides a comparison under
the new controls. One task still does not establish general SWE performance.

Config: `configs/experiments/model_31b_retry.toml`.
State/log: `runs/pipeline/model_31b_retry_v1/`.
Results: `experiments/results/model_31b_retry_v1/`.
The worker and study timers stop at completion or an infrastructure error.
