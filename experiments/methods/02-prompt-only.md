# 02 — Prompt-only adaptation

Question: does a model-proposed prompt improve behavior with an unchanged runtime?

- Freeze: 12B model, workflow source, sandbox, data and time/token/tool budgets.
- Run baseline first; generate exactly one candidate from agent-visible evidence.
- Vary only the system prompt, then evaluate the candidate in a fresh run.
- Keep both results and prompt texts even when the candidate fails.
- Config: `configs/experiments/prompt_only.toml`.
- State: `runs/pipeline/prompt_only_12b_v1/state.json`.

Model changes and manual runtime fixes require a separate experiment version.
Candidate acceptance on the toy issue is provisional, not proof of general improvement.
