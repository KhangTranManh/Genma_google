"""Versioned self-proposals based exclusively on agent-visible evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from .client import VllmClient
from .runs import write_json
from .serving import endpoint, health
from .experiments import identity, validate_selection, workflow_fingerprint


def feedback(run):
    run = Path(run)
    issue = json.loads((run / 'agent_input.json').read_text())
    manifest = json.loads((run / 'manifest.json').read_text())
    evidence = []
    # Deliberately never read evaluation.json, baseline-evaluation.json or reference patches.
    with (run / 'trajectory.jsonl').open() as stream:
        for line in stream:
            event = json.loads(line)
            if event['event'] in ('tool_call', 'tool_result', 'finished', 'compacted', 'truncated'):
                evidence.append(json.dumps(event, ensure_ascii=False)[:900])
    return {'issue': issue, 'agent_outcome': manifest.get('agent', {}),
            'recent_agent_events': '\n'.join(evidence)[-6500:]}


def parse_proposal(text):
    proposal = json.loads(text)
    if not isinstance(proposal, dict) or set(proposal) != {'system_prompt', 'rationale'}:
        raise ValueError('Expected system_prompt and rationale strings')
    prompt, reason = proposal['system_prompt'], proposal['rationale']
    if not isinstance(prompt, str) or not 100 <= len(prompt) <= 4500:
        raise ValueError('Candidate prompt must be 100–4500 characters')
    if not isinstance(reason, str) or not 1 <= len(reason) <= 2500:
        raise ValueError('Invalid rationale length')
    if 'submit_patch' not in prompt:
        raise ValueError('Candidate must preserve submit_patch protocol')
    return proposal


def propose(project, run, model_key, model):
    validate_selection(project, model_key)
    experiment = identity(project)
    if experiment['method'] == 'model_sweep':
        raise ValueError('Use the prompt_only experiment to propose prompt changes')
    health(project, model)
    run = Path(run).resolve()
    if experiment['method'] != 'legacy_mixed':
        source = json.loads((run / 'manifest.json').read_text())
        if source.get('experiment', {}).get('id') != experiment['id'] or source.get('model_key') != model_key:
            raise ValueError('Prompt feedback must come from the same isolated experiment and model')
        if source.get('workflow_sha256') != workflow_fingerprint(project.root)[0]:
            raise ValueError('Workflow changed since source run; create a new baseline')
    current = run / 'system_prompt.md'
    if not current.is_file():
        raise ValueError('Source run has no system_prompt.md snapshot; use a new local run')
    data = feedback(run)
    data['current_system_prompt'] = current.read_text()
    optimizer = (project.root / 'prompts/optimizer.md').read_text()
    client = VllmClient(endpoint(project), model['alias'], max_tokens=2048, thinking=False)
    response = client.complete([{'role': 'system', 'content': optimizer},
                                {'role': 'user', 'content': json.dumps(data, ensure_ascii=False)}],
                               [], timeout=120, response_format={'type': 'json_object'})
    write_json(run / 'prompt-proposal-response.json', response)
    if response['choices'][0]['finish_reason'] == 'length':
        raise ValueError('Prompt proposal truncated; original prompt is unchanged')
    proposal = parse_proposal(response['choices'][0]['message']['content'])
    digest = hashlib.sha256(proposal['system_prompt'].encode()).hexdigest()[:12]
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + digest
    folder = project.path('runs') / 'prompt-versions' / version
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / 'system.md'
    path.write_text(proposal['system_prompt'] + '\n')
    write_json(folder / 'proposal.json', {'version': version, 'source_run': str(run),
               'model_key': model_key, 'model': model['alias'], 'rationale': proposal['rationale'],
               'activated_as_default': False})
    print('Candidate prompt:', path, flush=True)
    return path
