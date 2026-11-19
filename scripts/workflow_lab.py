"""Isolated workflow-code experiment; one bounded action per trigger."""
import argparse
import ast
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gemma_lab.client import VllmClient
from gemma_lab.config import load
from gemma_lab.experiments import archive_results, digest_file, invariants
from gemma_lab.local import evaluate
from gemma_lab.prompts import feedback
from gemma_lab.provisioning import start_model
from gemma_lab.runs import prepare, write_json
from gemma_lab.serving import endpoint
from workflow_rpc import RUNTIME_FILES, run_runtime, validate_runtime

ALLOWED = ('src/gemma_lab/agent.py', 'docker/local/tools.py')
TERMINAL = {'complete', 'needs_review'}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    write_json(temporary, value)
    temporary.replace(path)


def frozen(project):
    record = invariants(project)
    control = ['scripts/workflow_lab.py', 'scripts/workflow_rpc.py', 'docker/workflow_runtime/runner.py', 'tests/test_agent.py']
    record['sandbox_image_id'] = subprocess.check_output(['docker', 'image', 'inspect', settings_image(project), '--format', '{{.Id}}'], text=True, timeout=15).strip()
    record['controller_sha256'] = hashlib.sha256(json.dumps({name: digest_file(project.root / name) for name in control}, sort_keys=True).encode()).hexdigest()
    return record


def settings_image(project):
    return project.raw['workflow']['image']


def source_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def parse_edits(proposal, baseline):
    if not isinstance(proposal, dict) or set(proposal) != {'edits', 'rationale'}:
        raise ValueError('Expected edits and rationale')
    edits = proposal['edits']
    if not isinstance(edits, list) or not 1 <= len(edits) <= 4 or not isinstance(proposal['rationale'], str):
        raise ValueError('Expected 1–4 source edits and a rationale string')
    candidate = dict(baseline)
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'path', 'old_string', 'new_string'}:
            raise ValueError('Malformed edit')
        name = edit['path']
        if name not in ALLOWED:
            raise ValueError('Edit outside the permitted workflow source files')
        old, new = edit['old_string'], edit['new_string']
        if not all(isinstance(value, str) and len(value) <= 16000 for value in (old, new)) or not old or old == new:
            raise ValueError('Invalid or empty source edit')
        if any(marker in new.lower() for marker in ('urlkit', 'append_query', 'example.com')):
            raise ValueError('Repository-specific code is not a general workflow improvement')
        if candidate[name].count(old) != 1:
            raise ValueError('old_string must match exactly once in the source snapshot')
        candidate[name] = candidate[name].replace(old, new, 1)
    for name, text in candidate.items():
        if len(text) > 100000:
            raise ValueError('Candidate source size exceeded')
        ast.parse(text, filename=name)  # Syntax only; never import/execute candidate code on the host.
    if candidate == baseline:
        raise ValueError('Candidate does not change source')
    return candidate


def candidate_decision(baseline, candidate, tests_passed):
    if not tests_passed or candidate is None:
        return 'rejected_validation'
    if candidate['status'] != 'local_pass':
        return 'rejected_task_result'
    if baseline['status'] != 'local_pass':
        return 'provisional_improvement'
    old_tokens = (baseline.get('agent') or {}).get('usage', {}).get('completion_tokens', 0)
    new_tokens = (candidate.get('agent') or {}).get('usage', {}).get('completion_tokens', 0)
    faster = candidate['elapsed_seconds'] <= baseline['elapsed_seconds'] * 0.95
    fewer = old_tokens > 0 and new_tokens <= old_tokens * 0.95
    if (faster or fewer) and candidate['elapsed_seconds'] <= baseline['elapsed_seconds'] * 1.10:
        return 'provisional_improvement'
    return 'no_measured_improvement'


def make_repository(project, directory):
    shutil.copytree(project.root / 'examples/urlkit_repo', directory, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    for command in (['git', 'init', '-q'], ['git', 'add', '-A'],
                    ['git', '-c', 'user.name=GemmaLab', '-c', 'user.email=local@example.invalid', 'commit', '-qm', 'baseline']):
        subprocess.run(command, cwd=directory, capture_output=True, check=True)
    commit = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
    return {'instance_id': 'demo-urlkit-query', 'repo': 'local/urlkit', 'base_commit': commit,
            'problem_statement': (project.root / 'examples/urlkit_issue.md').read_text()}


def pair_run(project, variant, files):
    key, model = project.select('model')
    settings = dict(project.raw['workflow'])
    settings['verification_command'] = 'python -m unittest discover -s tests -v'
    client = VllmClient(endpoint(project), model['alias'], settings['max_output_tokens'], settings['thinking'])
    with tempfile.TemporaryDirectory(prefix='workflow-source-', dir=project.path('runs')) as directory:
        task = make_repository(project, Path(directory))
        run = prepare(project, task, key, model)
        manifest_path = run / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest.update(status='running', backend='isolated_workflow_rpc', workflow_variant=variant,
                        variant_workflow_sha256=source_digest(files), workflow=settings, competition_score=False, frozen_controls=frozen(project))
        system = (project.root / settings['system_prompt']).read_text()
        (run / 'system_prompt.md').write_text(system)
        manifest['prompt_sha256'] = digest_file(run / 'system_prompt.md')
        write_json(manifest_path, manifest)
        with tarfile.open(run / 'variant-source.tar.gz', 'w:gz') as archive:
            for name, text in files.items():
                data = text.encode()
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
        started = time.monotonic()
        try:
            issue = f"Repository: {task['repo']}\nVerification command: {settings['verification_command']}\nIssue:\n{task['problem_statement']}"
            outcome = run_runtime(project.root, Path(directory), task['base_commit'], settings,
                                  client, issue, system, run, files)
            manifest['agent'] = outcome
            if outcome['reason'] == 'submitted':
                # Both public and independent validation use fresh trusted containers, not candidate helpers.
                patch = (run / 'patch.diff').read_text()
                public = run_public(project, Path(directory), task['base_commit'], patch)
                write_json(run / 'public-test-result.json', public)
                result = evaluate(settings, Path(directory), task['base_commit'], patch,
                                  project.root / 'examples/evaluation/test_urlkit.py')
                write_json(run / 'evaluation.json', result)
                changed_tests = any(line.startswith('diff --git ') and (' b/tests/' in line or '/tests/' in line or '/test_' in line or line.endswith('_test.py'))
                                    for line in patch.splitlines())
                manifest['regression_test_changed'] = changed_tests
                passed = public['exit_code'] == result['exit_code'] == 0 and not public['timed_out'] and not result['timed_out']
                if settings.get('require_regression_tests') and not changed_tests:
                    passed = False
                    manifest['validation_error'] = 'No regression-test change in the actual patch'
                manifest['status'] = 'local_pass' if passed else 'local_fail'
            else:
                manifest['status'] = 'incomplete'
        except Exception as error:
            manifest.update(status='failed', error=str(error))
        finally:
            manifest['elapsed_seconds'] = round(time.monotonic() - started, 3)
            manifest['code_changed_during_run'] = frozen(project) != manifest['frozen_controls']
            write_json(manifest_path, manifest)
        print('Workflow trial:', variant, run, manifest['status'], flush=True)
        return run, manifest


def run_public(project, repository, commit, patch):
    from gemma_lab.sandbox import DockerSandbox
    settings = project.raw['workflow']
    with DockerSandbox(settings['image'], settings['command_timeout_seconds'], settings['tool_output_chars']) as clean:
        clean.checkout(repository, commit)
        clean.apply_patch(patch)
        return clean.run_command('python -m unittest discover -s tests -v')


def propose(project, folder, baseline, run):
    key, model = project.select('model')
    evidence = feedback(run)
    evidence['recent_agent_events'] = evidence['recent_agent_events'][-1800:]
    user = {'workflow_source': baseline, 'feedback': evidence}
    system = ('Improve a reusable coding-agent workflow. Return only JSON with edits and rationale. '
              'edits must contain 1 to 4 objects with path, old_string, new_string, matching source exactly. '
              'Allowed paths: src/gemma_lab/agent.py and docker/local/tools.py. '
              'Fix a concrete general retry/context/file-tool weakness visible in the trajectory. '
              'Keep edits small; do not reproduce whole files. Do not hardcode repository names or task solutions. '
              'Do not modify prompts, evaluator, budgets, model selection, sandbox or host code. '
              'The revised Python runs in a container and must retain its public interfaces.')
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': json.dumps(user)}]
    # Check the installed server's tokenizer before reserving output space.
    request = urllib.request.Request(endpoint(project).removesuffix('/v1') + '/tokenize',
        data=json.dumps({'model': model['alias'], 'messages': messages, 'add_generation_prompt': True}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        tokens = json.load(response)['count']
    output = min(1536, project.raw['serving']['max_model_len'] - tokens - 256)
    if output < 512:
        raise ValueError('Workflow proposal does not fit model context; no candidate generated')
    result = VllmClient(endpoint(project), model['alias'], output, False).complete(
        messages, [], timeout=150, response_format={'type': 'json_object'})
    write_json(folder / 'proposal-response.json', result)
    if result['choices'][0]['finish_reason'] == 'length':
        raise ValueError('Workflow proposal truncated')
    proposal = json.loads(result['choices'][0]['message']['content'])
    candidate = parse_edits(proposal, baseline)
    write_json(folder / 'candidate.json', candidate)
    write_json(folder / 'proposal.json', proposal)
    diff = ''.join(''.join(difflib.unified_diff(baseline[name].splitlines(True), candidate[name].splitlines(True),
                                             fromfile='a/' + name, tofile='b/' + name)) for name in ALLOWED)
    (folder / 'workflow.patch').write_text(diff)
    return candidate


def tick(project, state, folder):
    key, model = project.select('model')
    phase = state['phase']
    if phase in TERMINAL:
        return
    start_model(project, key, model)
    baseline = json.loads((folder / 'baseline.json').read_text())
    settings = project.raw['workflow']
    if phase == 'baseline':
        validation = validate_runtime(project.root, settings, baseline)
        write_json(folder / 'baseline-validation.json', validation)
        if validation['exit_code'] != 0 or validation['timed_out']:
            raise RuntimeError('Baseline runtime unit validation failed')
        run, manifest = pair_run(project, 'baseline', baseline)
        state.update(phase='propose', baseline_run=str(run), baseline_result=manifest['status'])
    elif phase == 'propose':
        try:
            candidate = propose(project, folder, baseline, Path(state['baseline_run']))
            state['candidate_source_sha256'] = source_digest(candidate)
            state['phase'] = 'validate'
        except (ValueError, SyntaxError) as error:
            state.update(phase='finalize', candidate_rejection=str(error))
    elif phase == 'validate':
        candidate = json.loads((folder / 'candidate.json').read_text())
        if source_digest(candidate) != state['candidate_source_sha256']:
            raise RuntimeError('Candidate changed after proposal')
        validation = validate_runtime(project.root, settings, candidate)
        write_json(folder / 'candidate-validation.json', validation)
        state['candidate_unit_passed'] = validation['exit_code'] == 0 and not validation['timed_out']
        state['phase'] = 'candidate' if state['candidate_unit_passed'] else 'finalize'
    elif phase == 'candidate':
        candidate = json.loads((folder / 'candidate.json').read_text())
        if source_digest(candidate) != state['candidate_source_sha256']:
            raise RuntimeError('Candidate changed after validation')
        run, manifest = pair_run(project, 'candidate', candidate)
        state.update(phase='finalize', candidate_run=str(run), candidate_result=manifest['status'])
    elif phase == 'finalize':
        base = json.loads((Path(state['baseline_run']) / 'manifest.json').read_text())
        candidate = json.loads((Path(state['candidate_run']) / 'manifest.json').read_text()) if state.get('candidate_run') else None
        state.update(phase='complete', decision=candidate_decision(base, candidate, state.get('candidate_unit_passed', False)),
                     production_workflow_modified=False, promotion_scope='artifact_only_not_deployment')
        atomic_json(folder / 'decision.json', {'decision': state['decision'], 'production_workflow_modified': False,
            'baseline_run': state['baseline_run'], 'candidate_run': state.get('candidate_run'),
            'limitation': 'One synthetic task and one paired trial; any improvement is provisional.'})
    else:
        raise ValueError('Unknown workflow experiment phase')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/experiments/workflow_code_v2.toml')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop-timer-on-terminal', action='store_true')
    args = parser.parse_args(argv)
    project = load(args.config)
    change = project.raw['workflow_changes']
    if change.get('status') != 'enabled_isolated' or change.get('promotion') != 'artifact_only':
        raise ValueError('Use the explicitly enabled isolated workflow-code configuration')
    if change.get('proposal_count') != 1 or change.get('paired_repeats') != 1:
        raise ValueError('This initial implementation supports one proposal and one paired trial')
    folder = project.path('runs') / 'pipeline' / project.raw['experiment']['id']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'state.json'
    if args.status:
        print(path.read_text() if path.exists() else 'Workflow experiment not initialized')
        return 0
    lockfile = project.path('runs') / 'pipeline/shared-worker.lock'
    with lockfile.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another experiment is active; waiting for next trigger', flush=True)
            return 0
        state = json.loads(path.read_text()) if path.exists() else {
            'phase': 'baseline', 'experiment': project.raw['experiment'], 'in_progress': False, 'invariants': frozen(project)}
        if not (folder / 'baseline.json').exists():
            atomic_json(folder / 'baseline.json', {name: (project.root / name).read_text() for name in ALLOWED})
        try:
            if state.get('in_progress'):
                raise RuntimeError('Previous workflow-code phase was interrupted; inspect artifacts')
            if state['invariants'] != frozen(project):
                raise RuntimeError('Frozen controls changed; start a new experiment version')
            state['in_progress'] = True
            atomic_json(path, state)
            tick(project, state, folder)
            if state['invariants'] != frozen(project):
                raise RuntimeError('Frozen controls changed during a phase')
        except Exception as error:
            state.update(phase='needs_review', error=str(error))
        finally:
            state['in_progress'] = False
            state['updated_at'] = datetime.now(timezone.utc).isoformat()
            atomic_json(path, state)
            archive_results(project)
            print(json.dumps(state, indent=2), flush=True)
            if state['phase'] in TERMINAL and args.stop_timer_on_terminal:
                subprocess.run(['systemctl', 'stop', 'gemma-lab-workflow.timer'], check=False)
    return 1 if state['phase'] == 'needs_review' else 0

if __name__ == '__main__':
    raise SystemExit(main())
