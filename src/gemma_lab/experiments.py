"""Experiment identity, reproducibility records, and independent result archives."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

METHODS = {'model_sweep', 'prompt_only', 'workflow_code'}

def digest_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def workflow_files(root):
    files = set((root / 'src/gemma_lab').glob('*.py'))
    files.update((root / 'docker/local').glob('*.py'))
    for name in ('docker/local/Dockerfile', 'configs/local-requirements.lock'):
        if (root / name).is_file():
            files.add(root / name)
    return sorted(files)


def workflow_fingerprint(root):
    entries = {str(path.relative_to(root)): digest_file(path) for path in workflow_files(root)}
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(), entries


def identity(project):
    experiment = project.raw.get('experiment')
    if not experiment:
        return {'id': 'legacy_mixed', 'method': 'legacy_mixed', 'comparison_valid': False}
    if not re.fullmatch(r'[a-z0-9_-]+', experiment['id']):
        raise ValueError('Invalid experiment id')
    if experiment['method'] not in METHODS:
        raise ValueError('Unknown experiment method')
    return {'id': experiment['id'], 'method': experiment['method'], 'comparison_valid': True}


def invariants(project):
    files = sorted(path for path in (project.root / 'examples').rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts)
    dataset = {str(path.relative_to(project.root)): digest_file(path) for path in files}
    return {'workflow_sha256': workflow_fingerprint(project.root)[0],
            'baseline_prompt_sha256': digest_file(project.root / project.raw['workflow']['system_prompt']),
            'dataset_sha256': hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest(),
            'settings_sha256': hashlib.sha256(json.dumps(project.raw, sort_keys=True).encode()).hexdigest()}


def validate_selection(project, model_key, prompt=None):
    item = identity(project)
    method = item['method']
    if method == 'workflow_code':
        raise ValueError('workflow_code is definition-only; no workflow self-editing is enabled yet')
    if method == 'prompt_only' and model_key != project.raw['defaults']['model']:
        raise ValueError('prompt_only fixes the model; use a different experiment for model changes')
    if method == 'model_sweep' and prompt is not None:
        configured = project.root / project.raw['workflow']['system_prompt']
        if digest_file(prompt) != digest_file(configured):
            raise ValueError('model_sweep fixes the prompt; use prompt_only for prompt changes')
    return item


def archive_results(project, legacy=False):
    records = []
    base = project.root / 'experiments/results'
    for manifest_path in sorted(project.path('runs').glob('*/manifest.json')):
        run = manifest_path.parent
        manifest = json.loads(manifest_path.read_text())
        if manifest['status'] in ('running', 'prepared'):
            continue
        experiment = manifest.get('experiment', {'id': 'legacy_mixed', 'method': 'legacy_mixed', 'comparison_valid': False})
        # Existing runs are never retroactively relabelled as controlled experiments.
        method = experiment['method']
        destination = base / experiment['id'] / run.name
        destination.mkdir(parents=True, exist_ok=True)
        raw = destination / 'raw.tar.gz'
        if not raw.exists():
            with tarfile.open(raw, 'w:gz') as archive:
                for path in sorted(run.iterdir()):
                    if path.is_file() and not path.is_symlink():
                        archive.add(path, arcname=path.name)
        prompt = run / 'system_prompt.md'
        summary = {'run_id': run.name, 'experiment_id': experiment['id'], 'method': method,
                   'comparison_valid': experiment.get('comparison_valid', False),
                   'model': manifest.get('model_key'), 'task': manifest.get('instance_id'),
                   'status': manifest['status'], 'elapsed_seconds': manifest.get('elapsed_seconds'),
                   'agent': manifest.get('agent'), 'error': manifest.get('error'),
                   'prompt_sha256': digest_file(prompt) if prompt.exists() else None,
                   'workflow_sha256': manifest.get('workflow_sha256'),
                   'workflow_variant': manifest.get('workflow_variant'),
                   'variant_workflow_sha256': manifest.get('variant_workflow_sha256'),
                   'raw_sha256': digest_file(raw), 'source_run': str(run.relative_to(project.root))}
        if method == 'legacy_mixed':
            summary['limitation'] = 'Historical runs changed model, prompt and/or harness code; do not attribute gains to one method.'
        (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        records.append(summary)
    base.mkdir(parents=True, exist_ok=True)
    (base / 'index.json').write_text(json.dumps(records, indent=2) + '\n')
    for experiment_id in sorted({record['experiment_id'] for record in records}):
        rows = [record for record in records if record['experiment_id'] == experiment_id]
        folder = base / experiment_id
        (folder / 'index.json').write_text(json.dumps(rows, indent=2) + '\n')
        lines = ['# ' + experiment_id, '', '| Run | Model | Status | Seconds |', '|---|---|---|---|']
        for row in rows:
            lines.append(f"| [{row['run_id']}]({row['run_id']}/summary.json) | {row['model']} | {row['status']} | {row['elapsed_seconds']} |")
        (folder / 'README.md').write_text('\n'.join(lines) + '\n')
    old_state = project.path('runs') / 'pipeline/state.json' 
    if legacy and old_state.exists():
        folder = base / 'legacy_mixed'
        folder.mkdir(exist_ok=True)
        target = folder / 'pipeline-state.json'
        if not target.exists():
            target.write_bytes(old_state.read_bytes())
    return records
