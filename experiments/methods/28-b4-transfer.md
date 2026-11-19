# B4 v1 — transfer to sibling regex-performance issues

Roadmap step B4 (method 26), round 1: w3lib_266 (`get_meta_refresh`), w3lib_268 (`replace_tags` / `remove_tags`, two regions), w3lib_271 (`remove_tags_with_content`). Snapshots, locks and images are from the public FreshSWE dataset (`scripts/b4/prepare.py`). w3lib_289 (function rewrite) and markdown_1621 (algorithmic, non-regex) are deferred to round 2.

## Inputs

- **Issue:** sanitized and hand-written from the upstream text, keeping the title, the reproducer and the timings. The upstream "cause" and "suggested fix" sections, which state `[^<>]`, are removed (`experiments/b4_v1/tasks.json`).
- **Source:** the host supplies the exact excerpt or excerpts the upstream fix touches (regions in `tasks.json`). Unchanged sibling regexes already fixed earlier upstream (e.g. `_baseurl_re` with `[^<>]*`) remain visible elsewhere in the real file, but not in the excerpts.
- **Diagnose and Patch prompts:** same templates as B2 (`experiments/b23_v1/cases.json`), with checklist G frozen since hint ladder v2 and not edited after seeing these issues. Diagnose also receives the public timing of the original at three sizes.

## Procedure

- **Samples per task:** 31B gets t0 plus seeds 17/29/43 (4); 12B gets t0 plus 5 seeds (6). Each sample runs its own Diagnose and then Patch.
- **Guard:** B1 multi-edit guard (`check_edits`). Each edit must lie inside a region; identical duplicate calls and a truncated trailing call are dropped. At most one mechanical re-ask.
- **Selection:** the harness picks the first sample in fixed order that passes all public checks. Hidden checks are graded on every sample for audit only.

## Grading (`scripts/b4/evaluate.py`; preflight `runs/b4-preflight-v1`: original fails, reference accepted, for all 3 tasks)

| | Check |
|---|---|
| Public | Reproducer median ≤ 0.2 s at the calibrated N (the original needs ≥ 0.5 s there); existing `tests/test_html.py`; differential vs original on plain HTML, generic corpus `scripts/b4/container_check.py` with 1,884 cases (every printable ASCII character in attribute values and text) and 2–5 calls per task |
| Hidden | Upstream test patch applied, full `tests/test_html.py`; growth at 4 sizes (largest ≤ 0.5 s, 4× input ≤ 8× time); differential vs original-or-reference over all cases |

A known-bad variant (`[^<>\s]*` on w3lib_271) is caught: 1,002 public disagreements.

## Separation and limits

31B and 12B are separate batches: `runs/b4-v1/<model>`, `reports/b4-v1/<model>`, no cross-model table.
These are three sibling issues from the same repository and the same bug class as w3lib_264; transfer here does not imply transfer to other bug classes. A few samples per task is a check, not a rate.
