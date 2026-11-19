# 03 v2 — Isolated workflow-code adaptation

Status: implemented, one proposal and one paired trial per experiment.
The old v1 definition and all previous results remain unchanged.

## Fixed controls

12B base model, original system prompt, synthetic URLKit issue and independent
checks, serving settings, task time/turn/tool budgets, sandbox boundary and host
validation code. Source, configuration, evaluator and Docker image fingerprints
are checked before and after each triggered phase.

## Editable copy

The model may propose small exact replacements in only:

- `src/gemma_lab/agent.py` — context, retry and submission strategy.
- `docker/local/tools.py` — container-side file and shell tool behavior.

Proposals are syntax checked and stored as JSON plus a unified diff. Host production
source is never overwritten or imported as candidate code. Candidate modules and
the frozen runtime unit tests execute inside a non-root Docker container with no
network, host mounts or Docker socket. Task tools execute in a second isolated
container. Only trusted host code can call vLLM, capture a real patch and invoke
independent validation in a fresh third container.

## Host-enforced boundary

A bounded JSON RPC channel keeps the system prompt and original issue fixed. The
host counts model calls and repository/snapshot operations, limits wall time and
stdout/stderr, and rejects modified Git history or fake submissions without an
actual patch. Candidate runtime clocks, counters and self-reported results are not
used as grading evidence. Public tests, regression-test changes and independent
checks are verified outside candidate code.

## Triggered phases

1. Validate the baseline runtime in Docker, then run the baseline on the issue.
2. Provide only agent-visible trajectory and allowed source to 12B for one proposal.
3. Run frozen unit tests against the proposed runtime in Docker.
4. If validation passes, run the candidate on the same issue using the same controls.
5. Save a separate decision and stop the timer.

Reject failed validation or failed task results. If the baseline fails and the
candidate passes, or both pass and time/tokens improve within the configured
criterion, mark `provisional_improvement`. Retain it as an artifact for further
experiments; no automatic production deployment occurs. One synthetic issue and
one pair are insufficient to establish general improvement.

## Artifacts and commands

Config: `configs/experiments/workflow_code_v2.toml`.
State/proposals/diffs/decision: `runs/pipeline/workflow_code_12b_v2/`.
Run manifests and trajectories: separate `runs/RUN_ID/` folders, tagged baseline
or candidate and carrying separate variant source hashes.

```bash
.venv/bin/python scripts/workflow_lab.py --status
.venv/bin/python scripts/install_workflow_trigger.py
systemctl start --no-block gemma-lab-workflow.service
```

The study coordinator updates the method-specific report and stops after this
stage completes. Infrastructure errors stop for review instead of retrying forever.
