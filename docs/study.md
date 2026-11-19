# Sequential study and automatic report

The study coordinator checks saved state every two minutes and exits immediately.
It does not keep an interactive model session or continuous monitoring process alive.
GPU work remains controlled by the experiment worker timer.

The ordered plan is `configs/study.toml`:

1. Finish the isolated E4B/12B/31B model sweep with fixed prompt, code and budget.
2. After the worker has fully exited, select the separate 12B prompt-only experiment.
   Run its own baseline, one model-proposed prompt, and a candidate evaluation.
3. Run workflow-code v2 with a baseline/candidate pair, frozen controls and
   candidate imports restricted to Docker. Retain changes as artifacts only.
4. Save the final Markdown/JSON report and stop the study timer.

An infrastructure error stops the study for review and produces an explicitly partial
report. The controller never resets failed experiment state, rewrites frozen runtime
source, mixes result queues, or claims a definition-only method has been evaluated.
Reports include incomplete/failed runs and distinguish public tests from the separate
synthetic evaluator. Historical mixed runs stay in their own section.

## Artifacts

- `runs/study/state.json`: coordinator progress.
- `runs/study/controller.log`: short-trigger logs.
- `reports/study-report.md`: current human-readable report in Vietnamese.
- `reports/study-report.json`: machine-readable evidence by method.
- `reports/archive/`: timestamped final/partial report snapshots.
- `experiments/results/EXPERIMENT_ID/`: separately archived results and raw evidence.

## Commands

```bash
.venv/bin/python scripts/install_study_trigger.py
.venv/bin/python scripts/study_runner.py --status
.venv/bin/python scripts/study_runner.py --report-only
systemctl list-timers 'gemma-lab*' --no-pager
```

The study installer touches only study units. Selecting an experiment updates only
worker/model units, preventing the two installers from overwriting each other's
configuration. Both timers are serialized by systemd; experiment workers additionally
share a file lock before accessing the model server.

To stop future scheduling, stop both timers:

```bash
systemctl stop gemma-lab-study.timer gemma-lab-worker.timer
```

Stopping timers does not interrupt an already-running GPU job. Current progress is
written to disk, so the report can be regenerated without running a new experiment.
The coordinator itself is outside the frozen agent runtime fingerprint; its tests and
reporting can be maintained without contaminating the currently running model sweep.
