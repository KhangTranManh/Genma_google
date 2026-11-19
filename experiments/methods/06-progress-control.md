# Controlled anti-loop / completion experiment

Nine trials: three models (31B, 12B, E4B) under three separately saved policies.
The fixed system prompt is `experiments/prompts/tool_recovery_v1.md`. vLLM settings,
issue, independent tests and task limits (900 seconds, 48 turns, 96 requested tools)
are identical. Each policy has its own config, state and result directory.

| Arm | Agent implementation | Completion |
|---|---|---|
| A: progress_baseline_v1 | Unchanged legacy AgentLoop | Explicit model submit_patch |
| B: progress_guard_v1 | ProgressAgent, repeat detection and phase memory | Explicit model submit_patch |
| C: progress_finish_v1 | Same progress guard + verified completion | Model or harness-origin submission |

The legacy AgentLoop source remains unchanged. Selecting `workflow.agent_policy`
chooses the new implementation without silently changing old experiment behavior.
The old automatically proposed workflow candidate remains rejected and is not used.

## Progress and recovery contract

- Hash the actual workspace diff after repository operations; code/test changes reset
  repeat detection and invalidate old successful verification.
- Cache recent implementation reads and the current phase outside conversational
  history, so context trimming does not erase progress.
- Permit two identical observations on the same version. Suppress further repeats
  with an explicit unexecuted result and a required next action.
- Failed equivalent test invocations share a key. A reproduced failure requires an
  implementation edit; it is not progress to rerun unchanged tests indefinitely.
- After two failed exact edits, offer write_file as the editing fallback. Do not
  guess how to decode extra escapes or change the meaning of source text.
- Stop a stalled episode at four suppressed repeats or sixteen actions without a workspace change or new implementation information.
  These thresholds are fixed for all models in this synthetic comparison.
- Suppressed operations cannot change verification state. Passing tests that mutate
  workspace files do not verify the resulting new version.

## Harness-origin completion (C only)

When both implementation and regression-test files have changed, run the frozen
public verification command once per workspace version. If it passes and the patch
is unchanged, save the diff/review record and apply the same submission checks.
Check the workspace version again after verification; only an unchanged, verified
patch may be captured as `harness_submitted`. Independent tests run afterward in a
fresh container and are never provided as feedback to the model.

Do not conflate this with autonomous model submission or official competition
compatibility. The manifest records `submission_origin=model|harness` separately.
No arm is declared successful just because it has a patch or public tests pass.

## Partial patches and timing

All arms preserve available diffs at budget/stall exit. `recovered.diff` is evaluated
separately and remains diagnostic: the primary outcome stays incomplete. Agent
elapsed time is captured before recovered-patch evaluation. Policy C's own
observations, public checks and review overhead remain part of its task time.

Outputs: `reports/anti-loop-comparison.md`, `.json` and `.csv`, with state under
`runs/pipeline/progress_{baseline,guard,finish}_v1/`. A short trigger advances each
bounded job, archives evidence and stops at completion or infrastructure failure.

This is one synthetic issue per arm/model, not a general SWE benchmark. Task
completion, quality, loop suppression and submission origin are separate outcomes.
