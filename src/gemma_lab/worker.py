"""One bounded pipeline action per timer invocation; durable state, no continuous watcher."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
from .config import load
from .local import demo
from .prompts import propose
from .provisioning import download, start_model
from .runs import write_json
from .experiments import identity, invariants, archive_results

TERMINAL_RUNS = {'local_pass', 'local_fail', 'incomplete', 'failed', 'interrupted', 'submitted'}


def state_path(project):
    item = identity(project)
    folder = project.path('runs') / 'pipeline'
    if item['id'] != 'legacy_mixed':
        folder = folder / item['id']
    return folder / 'state.json'


def save(path, state):
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    write_json(temporary, state)
    temporary.replace(path)


def advance(state, order):
    state['model_index'] += 1
    state['prompt_trials'] = 0
    state.pop('candidate_prompt', None)
    state['phase'] = 'complete' if state['model_index'] >= len(order) else 'provision'


def record_run(state, run, status, model_key):
    manifest = json.loads((Path(run) / 'manifest.json').read_text())
    state.setdefault('results', []).append({'model': model_key, 'run': str(run), 'status': status,
        'elapsed_seconds': manifest.get('elapsed_seconds'), 'agent': manifest.get('agent', {})})
    state['last_run'] = str(run)


def tick(project, state):
    order = project.raw['automation']['model_order']
    if state['phase'] in ('complete', 'needs_review', 'stopped'):
        return
    key = order[state['model_index']]
    _, model = project.select('model', key)
    phase = state['phase']
    strategy = project.raw['automation'].get('strategy', 'legacy_mixed')
    if strategy == 'workflow_code':
        raise ValueError('workflow_code is definition-only; self-editing is not enabled')
    if phase == 'await_seed':
        run = project.root / project.raw['automation']['seed_run']
        manifest = json.loads((run / 'manifest.json').read_text())
        status = manifest['status']
        if status not in TERMINAL_RUNS:
            print('Seed run is still active; waiting for next trigger', flush=True)
            return
        record_run(state, run, status, key)
        state['last_working_model'] = key
        if status == 'local_pass':
            state['active_prompt'] = manifest.get('workflow', {}).get('system_prompt', state['active_prompt'])
        advance(state, order)
    elif phase == 'provision':
        # A manually started solve must finish before the worker changes GPU models.
        active = subprocess.check_output(['docker', 'ps', '--filter', 'name=gemma-lab-', '--format', '{{.Names}}'], text=True).strip()
        if active:
            print('Local sandbox still active; deferring model switch', flush=True)
            return
        download(project, model)
        start_model(project, key, model)
        state.update(phase='demo', last_working_model=key)
    elif phase in ('demo', 'evaluate_prompt'):
        start_model(project, key, model)
        prompt = state.get('candidate_prompt') if phase == 'evaluate_prompt' else state['active_prompt']
        run, status = demo(project, key, model, prompt=project.root / prompt)
        record_run(state, run, status, key)
        if strategy == 'model_sweep':
            advance(state, order)
            return
        if strategy == 'prompt_only' and phase == 'demo':
            state['phase'] = 'propose_prompt'
            return
        if status == 'local_pass':
            state['active_prompt'] = str(prompt)
            advance(state, order)
        elif state.get('prompt_trials', 0) < project.raw['automation']['max_prompt_trials_per_model']:
            state['phase'] = 'propose_prompt'
        else:
            # A measured model failure is data; still try the next configured model size.
            advance(state, order)
    elif phase == 'propose_prompt':
        start_model(project, key, model)
        candidate = propose(project, state['last_run'], key, model)
        state['candidate_prompt'] = str(candidate)
        state['prompt_trials'] = state.get('prompt_trials', 0) + 1
        state['phase'] = 'evaluate_prompt'
    else:
        raise ValueError(f'Unknown pipeline phase: {phase}')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/project.toml')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop-timer-on-terminal', action='store_true')
    args = parser.parse_args(argv)
    project = load(args.config)
    path = state_path(project)
    if args.status:
        print(path.read_text() if path.exists() else 'Pipeline not initialized')
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    lockfile = project.path('runs') / 'pipeline/shared-worker.lock'
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another worker invocation is active')
            return 0
        item = identity(project)
        state = json.loads(path.read_text()) if path.exists() else {
            'phase': 'await_seed' if item['id'] == 'legacy_mixed' else 'provision',
            'model_index': 0, 'prompt_trials': 0, 'experiment': item,
            'active_prompt': project.raw['workflow']['system_prompt'], 'results': []}
        if item['id'] != 'legacy_mixed' and 'invariants' not in state:
            state['invariants'] = invariants(project)
        if state.get('in_progress'):
            state.update(phase='needs_review', error='Previous job was interrupted; inspect its log before resuming')
            save(path, state)
            return 1
        state['in_progress'] = True
        save(path, state)
        try:
            if item['id'] != 'legacy_mixed':
                if project.raw['automation'].get('strategy') != item['method']:
                    raise ValueError('Automation strategy must match the experiment method')
                if state['invariants'] != invariants(project):
                    raise ValueError('Frozen workflow, baseline prompt or dataset changed; start a new experiment version')
            tick(project, state)
        except BaseException as error:
            state.update(phase='needs_review', error=str(error))
            # Restore the last known working model after a failed model switch.
            if state.get('last_working_model'):
                try:
                    old_key = state['last_working_model']
                    start_model(project, old_key, project.select('model', old_key)[1])
                    state['restored_model'] = old_key
                except Exception as restore_error:
                    state['restore_error'] = str(restore_error)
            print('Pipeline needs review:', error, flush=True)
            return 1
        finally:
            state['in_progress'] = False
            save(path, state)
            archive_results(project)
            if args.stop_timer_on_terminal and state['phase'] in ('complete', 'needs_review', 'stopped'):
                subprocess.run(['systemctl', 'stop', 'gemma-lab-worker.timer'], check=False)
            print(json.dumps(state, indent=2), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
