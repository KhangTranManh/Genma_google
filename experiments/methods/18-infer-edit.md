# Infer edit v1 — definition only

Question: with the location and exact source block supplied, can each model infer a valid repair without the textual fix hint? This isolates repair inference from navigation and character-copy ability. It is not autonomous repository repair.

Critical leakage control: upstream w3lib_264 issue itself states the [^>] -> [^<>] repair. Archive original issue verbatim; use the same solution-redacted issue in BOTH new arms. Do not label the sanitized version verbatim upstream. The infer prompt and shared careful checklist must contain no replacement expression, expected arguments, reference patch or hidden test. Prior observations/training may still have exposed this public issue; this is not a held-out evaluation.

Design:12B/31B × explicit_fix/infer_fix × short/4K/12K =12 generations. Both arms share sanitized issue, generic careful checklist, exact source block, one edit tool, native adapter, temperature0, thinkingoff,512 output and16384 context. Explicit arm alone appends the textual change. For calibrated long contexts use the same repository background construction as method17, target±128 with server-tokenizer and actual-usage checks. Explicit guidance slightly reduces background at matched target size. Both inputs keep target block near end; this is not a needle retrieval test. One sample per cell, no statistical improvement claim.

Only one model generation and at most one edit_file call per cell; no retries. Preserve output IDs/raw native call, API parsed arguments and installed parser replay from that same generation. Independently execute raw/API calls in separate clean snapshot containers; record literal old_string match, official tool response and actual diff. An edit can be valid with a different replacement span; never grade by exact argument equality or exact reference patch equality alone.

Separate assessment layers:
1. Call validity: a single executable edit_file call, valid path/schema.
2. Character fidelity: old_string literal match; compare raw vs parsed to locate transformation.
3. Applied change: actual file modifications, no unintended files, syntax/import validity.
4. Functional behavior: existing focused tests in clean environment with command/output/exit code.
5. Issue regression: independent host-owned malformed-input performance/complexity check plus representative valid-base-URL checks. Model never sees hidden grader. Accept alternative correct repairs.

Grader implementation is PENDING. Before any model run, freeze checks and demonstrate unchanged base fails the regression while a host diagnostic fixed version passes; record baseline/fixed behavior and environment. Avoid a brittle single elapsed-time threshold: use bounded subprocesses, repeated measurements across increasing malformed-input sizes, predeclared thresholds and a timed-out classification. The diagnostic fixed version validates the grader only and must never enter model inputs. Functional tests alone are insufficient because67 existing tests passed on unchanged base previously. Grader uncertainty is inconclusive, not model failure.

Report columns: model, arm, measured input tokens, call validity, raw/API equality, literal match, edit success, public tests, regression check, final category, runtime. Final categories: no_call, unsupported_or_truncated_capture, invalid_call, old_string_mismatch, parser_difference, applied_but_tests_fail, applied_but_regression_fail, verified_local_fix, inconclusive_grader. Keep measured properties independent; parser difference may coexist with other categories. Explicit success + infer failure suggests inference sensitivity in this setup, not an intrinsic incapability. Both failing with exact source may involve interface or reproduction issues; use raw evidence. Both passing indicates this guided task remains too easy.

Artifacts planned runs/infer-edit-v1/{model}/{arm}/{context}; reports/infer-edit-v1. No service or timer installed, no generation performed. Config/cases/prompts defined now; runner and independent grader must be implemented before activation. Keep all previous experiments unchanged.

## Implementation update

Grader and runner implemented. Preflight reports/infer-edit-v1/preflight/summary.json usable=true. Baseline67 tests pass but growth8K/2K≈16 and30K times out3s; diagnostic fixed passes. Predeclared performance limits:3 samples at2K/4K/8K/30K, each3s timeout,30K median≤0.5s and8K/2K median ratio≤8 with0.005s denominator floor. Five normal URL assertions also required. Each raw/API execution runs focused67 tests plus this grader independently. Snapshot/model prompts never include trusted grader. Service gemma-infer-edit-v1, bounded12-cell worker under shared GPU lock; HTML updated after each cell. Config status describes launch readiness; live execution state is runs/infer-edit-v1/state.json. Earlier definition-only text is historical.
