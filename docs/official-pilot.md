# Official-library integration and independent real-repository pilot

## What is now verified

- Organizer starter obtained unauthenticated from the public Kaggle kernel API.
- Core wheels obtained from the public organizer dataset, version 31:
  adk-submission 0.2.13, adk-eval-core 0.1.0, swegemma 0.2.11.
- Installed separately in `.venv-official`; the main vLLM environment is unchanged.
- Declarative YAML for 12B and 31B compiles with the organizer compiler, competition
  limits and real SwegemmaContext tool registry. No custom host entrypoint is exported.
- ZIP archives: `dist/official/{12b,31b}/submission.zip`.
- Compiler validation is not a leaderboard submission, nor proof of task-solving performance.

## Data access and independent fallback

Competition tasks endpoint returned HTTP 401 and metric data returned HTTP 403
without credentials. No login, acceptance of rules or competition submission was
performed. Public wheelhouse and starter were accessible normally.

The fallback dataset is FreshSWE-Py by its original publisher on Kaggle, not a
mirror of gated competition tasks. Selected before model outcomes: the alphabetically
first issue-sourced task for each preselected repo:

| Task | Repo |
|---|---|
| w3lib_264 | scrapy/w3lib |
| packaging_1125 | pypa/packaging |
| platformdirs_540 | tox-dev/platformdirs |

Selection manifest and raw data stay in ignored `data/freshswe/`. Solution/test
patches remain trusted evaluator inputs and never enter model context. No baseline
competitor patches were downloaded or read. Snapshot, lock and input hashes freeze
before starting the queue.

Each pinned Python 3.13 task image is built in Docker. Runtime containers have no
network, no host source mounts or Docker socket, 4 GiB memory and 2 CPUs, following
the organizer ContainerManager defaults. Repository setup/code executes only inside
those containers. Baseline-fail/reference-pass calibration is separate from model
runs; all three tasks passed this environment check before activation.

## Model pilot

Six runs: three tasks per model, 12B first then 31B. Both use the same recovery
prompt for an initial official-runtime baseline. The completion prompt was faster
on the single 12B toy run but slower on 31B; it is not automatically promoted.
Budgets: 15 minutes, 48 LLM calls, 96 tool calls, 60-second command timeout,
300-second verification timeout. Official runtime captures patch and verifies in a
fresh container. Tests/public behavior are governed by that runtime, not local gates.

This is an independent integration pilot, not the official competition score.
Differences include 2 A16 vs official 4 L4, vLLM 0.33.0 vs wheelhouse vLLM, 8192 vs
32768 model context, and host dependencies resolved locally rather than a complete
wheelhouse recreation. For the smaller context, compaction threshold is 4096 tokens.
All resolved host dependencies are recorded in configs/official-host-requirements.lock.

`ProgressAgent` revision 2 is not used by the official runner. Only declarative
config/prompt settings transfer into these archives. In particular, autonomous
local submission success cannot be assumed to transfer.

## Trigger and evidence

`gemma-lab-official-pilot.timer` advances one bounded action at a time, shares the
GPU-worker lock and waits until the toy study is complete. Frozen input changes or
an interrupted action stop for review; source state is not silently overwritten.

State: `runs/official-pilot/state.json`; logs and per-task evidence under
`runs/official-pilot/{12b,31b}/TASK/`. Report:
`reports/official/integration-report.{html,md,json}` linked from the main HTML report.
The trigger stops at completion or needs_review.

Sources:
- https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent
- https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse
- https://www.kaggle.com/datasets/moshegolderson/freshswe-py
