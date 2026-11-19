# Hint ladder v2 — robustness of the 31B result, feedback for 12B

Follows method 24 (hint ladder v1). Same issue w3lib_264, same source block, tool schema, system message, output cap 1536, thinking off, 16K runtime, same four pre-registered graders (public reproducer, 67 functional tests, independent regression grader, long-attribute semantic check). `accepted` requires all four.

## 31B (separate batch `runs/hint-ladder-v2/31b`)

v1 showed 31B accepted at AB/ABC but not control/A. Hint B was written knowing the answer. v2 asks:

| Arm | Hints | Temp | Question |
|---|---|---|---|
| B | B only | 0 | Is the mechanism (A) needed, or is the tailored principle enough? |
| G | generic regex-performance checklist | 0 | Does a checklist not written for this file work? |
| AG | A + G | 0 | Mechanism + generic checklist. |
| AB_s17/29/43 | A + B | 0.6, seeds 17/29/43 | Is the v1 AB success stable under sampling? |
| AG_s17/29/43 | A + G | 0.6, seeds 17/29/43 | Same for the generic checklist. |

G is a reusable regex-performance checklist (lazy quantifiers don't fix failed-match scans; numeric bounds reject valid input; restrict the span so it cannot cross a token that begins a new candidate match; keep valid long inputs). Item 4 is the textbook remedy for this class, so G is generic for regex-performance bugs, not generic for all bugs.

## 12B (separate batch `runs/hint-ladder-v2/12b`)

v1 ABC was fast but excluded whitespace, breaking tags with attributes before href. v2: fresh ABC generation (r0, temp 0), then at most 2 public-feedback repair rounds (r1, r2) on the cumulative source, stopping early on public pass. The model sees its previous parsed call, the public reproducer result and the tail of the functional-test output. The independent grader and the semantic check stay hidden and never trigger retries. Every candidate is graded with all four graders.

## Separation and limits

31B and 12B are separate batches with separate state, preflight, frozen-input hashes and reports (`reports/hint-ladder-v2/<model>/`). No cross-model table. v1 results are not modified.
One issue; three seeds is a robustness check, not a rate. 12B feedback adds calls and tokens, so it is not equal-budget with v1.
