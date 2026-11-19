"""Organizer evaluator on an independent FreshSWE pilot, Docker only."""
import argparse
import asyncio
import dataclasses
import json
import os
import hashlib
import shutil
from pathlib import Path
import time
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
os.environ.setdefault('LITELLM_TELEMETRY', 'False')
os.environ.setdefault('OTEL_SDK_DISABLED', 'true')
os.environ.setdefault('OPENAI_API_KEY', 'EMPTY')
from adk_submission import ModelRegistry
from google.adk.models.lite_llm import LiteLlm
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.models import load_tasks
from swegemma.harness.verification import verify_task

ROOT = Path(__file__).resolve().parents[2]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+'\n')
    temporary.replace(path)


async def run(args):
    data = ROOT/'data/freshswe'
    task = next(t for t in load_tasks(data/'pilot-tasks.jsonl') if t.instance_id == args.task)
    alias = f'gemma-4-{args.model}-it-qat-w4a16-ct'
    models = ModelRegistry();models.register(alias, LiteLlm(model='openai/'+alias, api_base='http://127.0.0.1:8000/v1', api_key='EMPTY'))
    result_dir = Path(args.output).resolve();result_dir.mkdir(parents=True,exist_ok=True)
    submission = Path(args.submission_dir).resolve() if getattr(args, 'submission_dir', None) else ROOT/'submission_candidates'/args.model
    if not (submission/'agent.yaml').is_file():
        raise ValueError('Submission directory must contain agent.yaml')
    if getattr(args, 'experiment', None):
        snapshot = result_dir/'submission-snapshot'
        shutil.copytree(submission, snapshot)
        submission = snapshot
        dump(result_dir/'run-inputs.json', {
            'experiment':args.experiment, 'arm':args.arm, 'model':args.model,
            'runtime_version':getattr(args,'runtime_version','v1'),
            'local_vllm_max_model_len':16384 if getattr(args,'runtime_version','v1')=='v2' else 8192,
            'task':args.task, 'base_commit':task.base_commit,
            'prompt_sha256':hashlib.sha256((submission/'prompts/system.md').read_bytes()).hexdigest(),
            'submission_files':{str(p.relative_to(submission)):hashlib.sha256(p.read_bytes()).hexdigest() for p in submission.rglob('*') if p.is_file()},
            'dataset':'FreshSWE-Py development issues previously observed', 'official_competition_score':False})
    max_model_len=16384 if getattr(args,'runtime_version','v1')=='v2' else 8192
    config = EvalConfig(tasks_path=data/'pilot-tasks.jsonl', snapshots_dir=data/'snapshots', results_dir=result_dir,
                        submission_dir=submission, models=models,
                        image='gemma-official-pilot:'+args.task.lower(), sandbox='docker',
                        timeout_seconds=60, verification_timeout_seconds=300, max_time_minutes=15,
                        max_tool_calls=96, max_turns=48, graph_dir=str(data/'graphs'), embeddings_dir=str(data/'embeddings'),
                        events_compaction_config=EventsCompactionConfig(compaction_interval=10, overlap_size=2,
                                                                       token_threshold=4096, event_retention_size=5),
                        display_mode='quiet', verbose=False)
    evaluator = Evaluator(config)
    started = time.monotonic()
    try:
        if args.phase == 'preflight':
            # Trusted verifier only: no model receives the reference solution or test patch.
            baseline = await verify_task(evaluator.docker, config, task, data/'snapshots'/f'{args.task}.tgz', agent_patch='', start_time=time.perf_counter())
            gold = await verify_task(evaluator.docker, config, task, data/'snapshots'/f'{args.task}.tgz', agent_patch=task.patch, start_time=time.perf_counter())
            record = {'phase':'preflight', 'task':args.task, 'repo':task.repo, 'base_commit':task.base_commit,
                      'baseline_resolved':baseline.resolved, 'baseline_exit_code':baseline.test_exit_code,
                      'baseline_error':baseline.error, 'reference_resolved':gold.resolved,
                      'reference_exit_code':gold.test_exit_code, 'reference_error':gold.error,
                      'usable':not baseline.resolved and gold.resolved,
                      'seconds':round(time.monotonic()-started,3)}
            (result_dir/'baseline-output.txt').write_text(baseline.test_output)
            (result_dir/'reference-output.txt').write_text(gold.test_output)
        else:
            # Only issue/repo/hints enter the official task prompt. Full Task remains trusted host data.
            result = await evaluator.evaluate_task(task)
            record = result.model_dump(exclude={'trace', 'agent_patch'})
            record.update(phase='agent', model=args.model, task=args.task, official_competition_score=False,
                          dataset='FreshSWE-Py independent pilot', local_progress_agent_used=False,
                          local_vllm_max_model_len=max_model_len, compaction_token_threshold=4096,
                          experiment=getattr(args,'experiment',None), arm=getattr(args,'arm',None))
            (result_dir/'agent.patch').write_text(result.agent_patch)
            (result_dir/'test-output.txt').write_text(result.test_output)
        dump(result_dir/'summary.json',record)
        print(json.dumps(record,ensure_ascii=False,default=str),flush=True)
        return 0 if args.phase != 'preflight' or record['usable'] else 2
    finally:
        evaluator.docker.cleanup_all()


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--task',required=True)
    parser.add_argument('--model',choices=['12b','31b'],default='12b')
    parser.add_argument('--phase',choices=['preflight','agent'],required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--runtime-version',choices=['v1','v2'],default='v1')
    parser.add_argument('--submission-dir')
    parser.add_argument('--experiment')
    parser.add_argument('--arm',choices=['baseline','prompt','skill'])
    args=parser.parse_args()
    if bool(args.experiment) != bool(args.arm):
        parser.error('--experiment and --arm must be supplied together')
    raise SystemExit(asyncio.run(run(args)))
