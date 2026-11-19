"""Short timer-triggered checks; the experiment worker executes GPU jobs."""
from datetime import datetime, timezone
import argparse
import fcntl
from pathlib import Path
import subprocess
import sys
from study_report import generate, load_study, read_json, write_json

TERMINAL = {'complete', 'needs_review', 'stopped'}


def worker_busy():
    result = subprocess.run(['systemctl', 'show', 'gemma-lab-worker.service', '--property=ActiveState', '--value'],
                            check=True, capture_output=True, text=True)
    return result.stdout.strip() in {'active', 'activating', 'deactivating', 'reloading'}


def activate(root, profile, interval_seconds=300):
    subprocess.run([str(root / '.venv/bin/python'), str(root / 'scripts/install_triggers.py'),
                    '--experiment', profile, '--interval-seconds', str(interval_seconds)], check=True, timeout=60)
    subprocess.run(['systemctl', 'start', '--no-block', 'gemma-lab-worker.service'], check=True, timeout=15)


def tick(root, state):
    stages = load_study(root)['stages']
    if state.get('status') in {'complete', 'needs_review'}:
        return
    index = state.setdefault('stage_index', 0)
    if index >= len(stages):
        state['status'] = 'complete'
        return
    stage = stages[index]
    state['current_stage'] = stage['id']
    if stage['mode'] == 'definition':
        definition = root / stage['definition']
        if not definition.is_file():
            raise ValueError('Missing workflow-code definition')
        state.setdefault('definitions', {})[stage['id']] = {
            'status': 'defined_not_executed', 'path': stage['definition']}
        state['stage_index'] = index + 1
        state['status'] = 'complete' if index + 1 == len(stages) else 'running'
        return
    if stage['mode'] == 'metrics':
        existing = read_json(root / 'runs/pipeline' / stage['id'] / 'state.json')
        if existing.get('phase') == 'needs_review':
            state.update(status='needs_review', error=existing.get('error', 'Performance benchmark requires review'))
        elif existing.get('phase') == 'complete':
            state.setdefault('completed_stages', []).append(stage['id'])
            state.update(stage_index=index + 1, status='complete' if index + 1 == len(stages) else 'running')
        elif not existing:
            subprocess.run([str(root / '.venv/bin/python'), str(root / 'scripts/install_metrics_trigger.py')], check=True, timeout=60)
            subprocess.run(['systemctl', 'start', '--no-block', 'gemma-lab-metrics.service'], check=True, timeout=15)
            state['status'] = 'running'
        else:
            active = subprocess.run(['systemctl', 'is-active', 'gemma-lab-metrics.timer'], capture_output=True, text=True)
            state['status'] = 'running' if active.stdout.strip() == 'active' else 'needs_review'
            if state['status'] == 'needs_review':
                state['error'] = 'Performance benchmark incomplete but timer is inactive'
        return
    if stage['mode'] == 'workflow_experiment':
        existing = read_json(root / 'runs/pipeline' / stage['id'] / 'state.json')
        if existing.get('phase') == 'needs_review':
            state.update(status='needs_review', error=existing.get('error', 'Workflow trial requires review'))
        elif existing.get('phase') == 'complete':
            state.setdefault('completed_stages', []).append(stage['id'])
            state.update(stage_index=index + 1, status='complete' if index + 1 == len(stages) else 'running')
        elif not existing:
            subprocess.run([str(root / '.venv/bin/python'), str(root / 'scripts/install_workflow_trigger.py')], check=True, timeout=60)
            subprocess.run(['systemctl', 'start', '--no-block', 'gemma-lab-workflow.service'], check=True, timeout=15)
            state['status'] = 'running'
        else:
            active = subprocess.run(['systemctl', 'is-active', 'gemma-lab-workflow.timer'], capture_output=True, text=True)
            state['status'] = 'running' if active.stdout.strip() == 'active' else 'needs_review'
            if state['status'] == 'needs_review':
                state['error'] = 'Workflow trial incomplete but its timer is inactive'
        return
    existing = read_json(root / 'runs/pipeline' / stage['id'] / 'state.json')
    if existing.get('phase') in {'needs_review', 'stopped'}:
        state.update(status='needs_review', error=existing.get('error', 'Experiment requires review'))
        return
    if existing.get('phase') == 'complete':
        if worker_busy():
            state['status'] = 'waiting_for_worker_cleanup'
            return
        state.setdefault('completed_stages', []).append(stage['id'])
        state['stage_index'] = index + 1
        state['status'] = 'running'
        return
    marker = read_json(root / 'runs/pipeline/active-experiment.json')
    if marker.get('profile') != stage['profile'] or not existing:
        if worker_busy():
            state['status'] = 'waiting_for_worker'
            return
        activate(root, stage['profile'], stage.get('interval_seconds', 300))
        state['status'] = 'running'
        return
    timer = subprocess.run(['systemctl', 'is-active', 'gemma-lab-worker.timer'], capture_output=True, text=True)
    if timer.stdout.strip() != 'active' and not worker_busy():
        state.update(status='needs_review', error='Experiment incomplete but worker timer is inactive; inspect before resuming')
        return
    state['status'] = 'running'


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    parser.add_argument('--stop-timer-on-terminal', action='store_true')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    folder = root / 'runs/study'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'state.json'
    if args.status:
        print(path.read_text() if path.exists() else 'Study not initialized')
        return 0
    if args.report_only:
        generate(root)
        return 0
    with (folder / 'controller.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        state = read_json(path, {'status': 'running', 'stage_index': 0})
        try:
            tick(root, state)
        except Exception as error:
            state.update(status='needs_review', error=str(error))
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_json(path, state)
        generate(root)
        if state['status'] in {'complete', 'needs_review'}:
            if args.stop_timer_on_terminal:
                subprocess.run(['systemctl', 'stop', 'gemma-lab-study.timer'], check=False)
            archive = root / 'reports/archive'
            archive.mkdir(exist_ok=True)
            name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            for suffix in ('md', 'json', 'html'):
                (archive / f'{name}-study-report.{suffix}').write_bytes((root / f'reports/study-report.{suffix}').read_bytes())
        print(state, flush=True)
        return 1 if state['status'] == 'needs_review' else 0

if __name__ == '__main__':
    raise SystemExit(main())
