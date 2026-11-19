# 01 — Model sweep

Question: how does changing model size affect solve rate, time and tool reliability?

- Vary: E4B, 12B, 31B.
- Freeze: system prompt, workflow code, test set, serving settings and per-task budget.
- No prompt optimizer runs in this method.
- Record every failed, timed-out and successful run separately.
- Config: `configs/experiments/model_sweep.toml`.
- State: `runs/pipeline/model_sweep_v1/state.json`.

The single synthetic issue only checks integration. Broader claims require a fixed
multi-repository development set and repeated runs. Historical mixed runs are excluded.
