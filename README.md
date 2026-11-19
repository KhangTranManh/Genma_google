# Gemma Lab

Config-driven local development for the Gemma 4 Developer Agent competition.
The inference backend is **vLLM**, exposed through its OpenAI-compatible API.
Python 3.11+ runs the orchestration CLI without third-party dependencies.

## Quick start

```bash
./gemma-lab doctor
./gemma-lab serve --model e4b --dry-run
python3 -m unittest discover -s tests -v
```

Edit `configs/project.toml` to change model checkpoint paths, GPU assignment,
vLLM settings, repository registry, and official harness commands.
Run commands from the project root, or pass an absolute `--config` path.

## Layout

```text
configs/project.toml       Model/repo registry, vLLM and harness configuration
src/gemma_lab/             CLI, agent loop, Docker tools, serving, task input, packaging
submission/               Competition payload only; official agent.yaml pending
third_party/              Official harness assets (local, ignored)
data/tasks.jsonl           Official public tasks (local, ignored)
models/                    Downloaded checkpoints (local, ignored)
runs/                      Per-run inputs, manifest, logs (local, ignored)
dist/                      Generated archives (local, ignored)
docker/local/              Local sandbox image and container-side tools
examples/                  Synthetic repo, issue and separate evaluator
tests/                     Workflow contract and isolation checks
docs/                      Architecture and integration instructions
```

## vLLM

Install a compatible vLLM environment separately, using the official wheelhouse/version
when supplied. `pip install -e '.[serve]'` is an optional convenience for experimentation;
it is not a verified competition dependency lock.
Point a model entry at an existing checkpoint before launching:

```bash
./gemma-lab serve --model e4b --dry-run
./gemma-lab serve --model e4b
# In another terminal:
./gemma-lab health --model e4b
```

Current configuration: GPUs 0 and 1, tensor parallel 2, context 8192, chunked
prefill with 512 tokens per batch. The two A16 GPUs communicate over PCIe through
the host bridge; throughput must be measured. Change `devices` and
`tensor_parallel_size` together to select another GPU layout.
No CPU fallback or alternate serving backend is silently selected.

## Tasks and runs

When the official tasks file is available:

```bash
./gemma-lab tasks --repo requests
./gemma-lab prepare --repo requests --model e4b --task ACTUAL_INSTANCE_ID
./gemma-lab run --repo requests --model e4b --task ACTUAL_INSTANCE_ID
```

`prepare` writes an allowlisted agent input and a configuration snapshot; it does not
execute the agent. `run` checks the vLLM model and invokes the configured official
harness. A successful harness process is recorded as `harness_finished`, not as a
solved issue. Only the official evaluator can establish pass/fail.

## Local agent workflow

```bash
docker build -t gemma-lab-sandbox:local docker/local
./gemma-lab demo --model e4b
# Public task data + exact local Git checkout required:
./gemma-lab solve --repo requests --task ACTUAL_INSTANCE_ID --checkout /path/to/repo
```

The agent inspects code, edits, runs tests and submits a Git patch through Docker tools.
The local submission check requests review, regression tests and passing public tests.
The demo evaluates in a fresh container using tests that were not exposed to the agent.
See [workflow details](docs/workflow.md) for limits, artifacts and repository setup.

## Separate experiment methods

Results are archived before new methods are defined. See [experiments](experiments/README.md)
for independent model-sweep, prompt-only and workflow-code profiles, and
[saved historical results](experiments/RESULTS.md). Workflow code adaptation v2 uses isolated candidate copies and a separate paired evaluation.
The legacy queue reached needs_review after the 31B timeout. The timer now runs
only the separate `model_sweep_v1` queue; prompt-only and workflow-code trials remain inactive.

## Anti-loop policy ablation

The next controlled study tests three models under three policies: unchanged baseline,
progress/repeat guard, and guard plus verified harness-assisted completion. The system
prompt and budgets stay fixed. [Definition](experiments/methods/06-progress-control.md)
and [A/B/C results](reports/anti-loop-comparison.md) distinguish autonomous submission,
harness-origin submission and diagnostic recovered patches.

## Matched three-model comparison

The extended comparison runs 31B, 12B and E4B with the same recovery prompt and
900-second task budget, then measures fixed-length streaming throughput, TTFT and
sampled VRAM through a separate trigger. The [comparison table](reports/model-comparison.md)
and [CSV](reports/model-comparison.csv) retain failures and missing measurements.
See [criteria and provenance](experiments/methods/05-three-model-comparison.md).

## Sequential study and report

A short study trigger checks progress every two minutes, finishes the model sweep,
then selects the separate prompt-only experiment and updates a method-by-method report.
Workflow-code adaptation v2 runs as a separate isolated stage. See [study automation](docs/study.md)
and the [current report](reports/study-report.md).

## Self-improvement and triggers

The model can propose a versioned system prompt from its own trajectory, then test
that candidate on the next run. A bounded systemd pipeline progresses through
E4B, 12B and 31B with at most one prompt trial per model. See
[automation instructions](docs/automation.md) for scheduling, logs and stop commands.

## Submission

Import the official sample into `submission/` and configure the official validator:

```bash
./gemma-lab package --model e4b
# For archive inspection before validator integration:
./gemma-lab package --model e4b --allow-unvalidated
```

Only files under `submission/` enter the ZIP; `agent.yaml` is required at the root.
Unvalidated archives are named `submission.unvalidated.zip`. YAML compilation,
include resolution, allowed tools, adapter compatibility and evaluation remain the
official harness's responsibility. See [integration instructions](docs/integration.md).

## Current status

Implemented: model/repo selection, vLLM serving, bounded local tool loop, Docker sandbox,
review/test submission checks, independent demo evaluation, trajectory logging,
task filtering, input isolation and submission packaging.
Local environment and checkpoint setup are documented in [local runtime](docs/local-runtime.md).
Pending competition integration: official assets, exact validator/evaluator CLI,
and an end-to-end scored task.

## Next development scope

Focus on 12B autonomous completion and 31B reliability; E4B is excluded from new
focus profiles, with prior results preserved. See the [two-model plan](experiments/methods/07-two-model-focus.md).
Profiles: `configs/experiments/focus_12b.toml` and `focus_31b.toml`. Defined, not yet executed.

The active follow-up is an eight-trial layer ablation on 12B/31B: fresh control,
prompt-only, harness-code-only, and runtime history configuration. See
[the design](experiments/methods/08-layer-ablation.md) and
[paired results](reports/two-model-layers.md). E4B is historical only.

Official compiler/validator integration is available in a separate environment.
The next independent pilot evaluates 12B/31B on three FreshSWE-Py repositories using
the organizer evaluator (not the local AgentLoop). See [integration details](docs/official-pilot.md)
and [the live pilot report](reports/official/integration-report.html).
Competition task data remains unavailable without accepting rules/authentication;
no Kaggle score or submission has been produced.

Focused reading is defined as a separate R0/R1/R2 experiment on 12B/31B, with six
compiler-validated candidates and no model runs scheduled yet. See
[the design](experiments/methods/10-focused-reading.md) and
[definition HTML](reports/reading-v1/definition.html).

The focused-reading execution queue is now implemented with separate worker and
read-only watch timers. It preserves 18 development cells, immutable input hashes,
explicit-submit versus fallback outcomes, and per-run traces. See the
[live reading comparison](reports/reading-v1/comparison.html).

The next diagnostic is defined separately: same-generation raw token IDs versus
parsed tool-call arguments, starting with four small cases on 12B/31B. The first eight capture-only requests are complete; no returned tools were executed.
Results distinguish tool choice from parser corruption. See
[the probe definition](experiments/methods/13-toolcall-parser-probe.md).

[Raw/parsed probe results](reports/toolcall-probe-v1/comparison.html) preserve token IDs,
raw native output, API response and replay from the same generation.
