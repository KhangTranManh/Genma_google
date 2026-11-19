# Separate experiments

Archive results first, then define and test one method at a time.

| Method | Variable | Fixed | Status |
|---|---|---|---|
| [Model sweep](methods/01-model-sweep.md) | Model size | Prompt and workflow | Defined, runnable |
| [Prompt only](methods/02-prompt-only.md) | System prompt | Model and workflow | Defined, runnable |
| [Workflow code v2](methods/03-workflow-code-v2.md) | Runtime source patch | Model and prompt | Isolated implementation |

The old pipeline is retained as `legacy_mixed`: historical runs changed several
factors and cannot identify the effect of one technique. See [saved results](RESULTS.md).

```bash
./gemma-lab archive-results
.venv/bin/python -m gemma_lab.worker --config configs/experiments/model_sweep.toml --status
.venv/bin/python -m gemma_lab.worker --config configs/experiments/prompt_only.toml --status
```

Each experiment has its own state directory. A shared lock prevents simultaneous
workers from competing for the GPU server. New experiments freeze hashes of workflow,
baseline prompt and example data; changed invariants stop the experiment for review.
Every new run stores its method, source fingerprint and workflow source archive.
Completed runs are archived under `experiments/results/EXPERIMENT_ID/RUN_ID/`.
The raw archive remains local and ignored by Git; summaries/index are reviewable files.

The timer now runs only `model_sweep_v1`, starting with E4B and progressing to 12B
and 31B. The historical legacy queue remains unchanged at needs_review. The study coordinator queues prompt-only
after this sweep completes; workflow-code v2 runs in its own isolated experiment after the earlier stages. The selected timer profile is
recorded in `runs/pipeline/active-experiment.json`.

```bash
.venv/bin/python scripts/install_triggers.py --experiment model_sweep
.venv/bin/python -m gemma_lab.worker --config configs/experiments/model_sweep.toml --status
```

The timer stops when its queue completes or needs review. Each method writes its own
result index and table; no aggregate score across methods is computed.
