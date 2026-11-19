# Hint ladder v1 — how much information the Patch step needs

Question: on the observed w3lib_264 issue, which level of added information lets the model produce an accepted patch?
Tool calls and edit execution are already known to work (methods 16–17); the failure point is choosing a correct repair (methods 18–23).

Arms (cumulative hints, text in `experiments/hint_ladder_v1/cases.json`):

| Arm | Added to the infer_fix prompt |
|---|---|
| control | Nothing; same prompt as infer_edit_v1 infer_fix short / budget_edit attempt_0. |
| A | Verified mechanism: per-start `[^>]*` scan to end of text, backtracking, O(n^2). |
| AB | A + design principle: bound each attempt to its own tag, stop at next tag start, no numeric length limit, minimal change. |
| ABC | AB + analogous example from a different pattern (`[^\]]*` → `[^\[\]]*`); the exact expression for this file is never given. |

Fixed: checkpoint, 16K runtime (reading-runtime-v2), tool schema, system message, temperature 0, thinking off, output cap 1536, one generation per arm, every arm starts from the original source. No feedback, no retries.

Grading (all pre-registered, applied to every candidate, never shown to the model, never used to select or retry):
public reproducer `"<base "*6000` median ≤ 0.2 s; 67 functional tests; independent regression grader (2K/4K/8K/30K growth + valid URL cases);
long-attribute semantic check (0/200/1000-char extra attribute). `accepted` requires all four. Raw and API calls executed separately in clean containers.
Per-model preflight confirms original fails and host diagnostic fix passes all graders.

Separation: each model is a separate batch — `runs/hint-ladder-v1/<model>/`, own state, frozen-input hashes, preflight and report
`reports/hint-ladder-v1/<model>/`. 12B runs first to completion, then 31B. No combined cross-model table is produced.

Limits: one issue, one generation per arm, temperature 0 — this is a diagnostic of the information gap on this issue, not a rate.
Hint B is close to the fix and C is structurally analogous; success at AB/ABC shows the model can apply guidance, not that it can find the fix.
Arms add prompt tokens, so they are not equal-input. No Kaggle submission.
