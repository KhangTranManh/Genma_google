# Generic pipeline v1 — no per-task hand definitions

This method replaces the hand-defined B4 setup. The model sees only the **verbatim dataset problem statement** (no sanitizing, as in the competition) and the repository snapshot. Nothing in the pipeline is written for a specific repository or bug class.

1. **Localize.** The model gets the issue, the list of source files (tests and docs excluded), and host grep hits for `def`/`class`/assignments of identifiers that appear in the issue. It returns up to 3 `{file, symbol}` targets. The host turns each target into the exact source span of that symbol (ast, read-only).
2. **Reproduce.** The model writes `repro.py` (exit 0 = fixed). The harness runs it on the original in the task container. It must fail there; if it does not, the model gets one retry with the observed output. Without a valid repro the pipeline continues, and the public check uses tests only.
3. **Patch.** 4 samples per task (t0, then seeds 17/29/43), with a generic repair guideline. Edits are restricted to the localized spans by the B1 multi-edit guard, with at most one mechanical re-ask.
4. **Public check.** The repro passes, and the related existing tests (test files that mention the touched modules, at most 4) gain no new failures compared with the original.
5. **Selection and grading.** The harness selects the first sample in fixed order that passes the public check. The hidden grade is the official `verify_task` with the dataset's FAIL_TO_PASS/PASS_TO_PASS tests. It runs on every applied candidate for audit only, and it is never shown to the model or used to select.

**Dev set:** 8 tasks from 8 repositories (`experiments/generic_v1/dev-tasks.json`), selected without looking at model outcomes. Each task's official preflight requires the baseline to be unresolved and the gold patch resolved (`runs/generic-preflight-v1`).

**Metrics**, one batch per model with no cross-model table:
- localization hit (a localized file is one of the gold files);
- repro valid;
- selected and resolved;
- any sample resolved.

## v3 changes (generic, after the generic-v2 review)

- **Repro validity.** A failure caused by the script itself no longer counts as a valid repro. This covers ImportError, ModuleNotFoundError, SyntaxError, NameError, FileNotFoundError and timeouts. Up to 3 tries, each told the reason for the rejection.
- **No tool call.** A reply with no tool call now gets its own notice ("respond only with edit_file calls") and one re-ask. Before, it was misreported as a no-op.
