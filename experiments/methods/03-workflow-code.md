# 03 — Workflow code adaptation (definition only)

Question: can model-proposed runtime code changes improve issue solving?

This method is not enabled yet. No job currently grants a model permission to edit
host workflow source. Implement it only after the earlier results have been archived
and each comparison has its own reproducible baseline.

- Freeze: 12B, baseline prompt, dataset/evaluator, sandbox boundary and resource budgets.
- Propose a patch on an isolated copy of the workflow.
- Initial editable scope: agent context/retry policy and container-side file tools.
- Keep evaluator, scheduler, sandbox boundary and acceptance criteria outside editable scope.
- Require unit/integration tests and paired evaluation before retaining a candidate.
- Store candidate source diff, source hashes, tests, trajectories and rejected variants.
- Config: `configs/experiments/workflow_code.toml` (execution is explicitly rejected).

Do not mix prompt edits, model scaling and workflow edits into the same candidate.
