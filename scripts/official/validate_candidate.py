"""Validate/compile with organizer libraries; does not claim scored compatibility."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import zipfile
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
os.environ.setdefault('LITELLM_TELEMETRY', 'False')
os.environ.setdefault('OTEL_SDK_DISABLED', 'true')
from adk_submission import compile_submission, validate_directory, ModelRegistry, discover_adapters
from google.adk.models.lite_llm import LiteLlm
from swegemma.config import build_submission_limits
from swegemma.context import SwegemmaContext

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {f'gemma-4-{s}-it-qat-w4a16-ct' for s in ['31b', '12b', 'e4b', 'e2b']}


def validate(folder, key, artifact_root=None, report_root=None):
    limits, constraints = build_submission_limits()
    validate_directory(folder, limits=limits)
    # Use official loader for includes and closed schema, not generic safe_load.
    from adk_submission.yaml_loader import load_yaml
    raw = load_yaml(folder / 'agent.yaml', folder)
    alias = raw['model']
    if alias != f'gemma-4-{key}-it-qat-w4a16-ct':
        raise ValueError('Candidate key does not match declared model')
    if alias not in ALLOWED:
        raise ValueError('Unsupported model')
    registry = ModelRegistry()
    registry.register(alias, LiteLlm(model='openai/' + alias, api_base='http://127.0.0.1:8000/v1', api_key='EMPTY'))
    tools = SwegemmaContext(max_tool_calls=96, max_time_minutes=15).create_tools()
    adapters = discover_adapters(str(folder))
    agent = compile_submission(folder, tool_registry=tools, model_registry=registry,
                               limits=limits, generation_constraints=constraints, adapter_manifest=adapters)
    archive = (Path(artifact_root) if artifact_root is not None else ROOT / 'dist/official') / key / 'submission.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for file in sorted(folder.rglob('*')):
            if file.is_symlink():
                raise ValueError('No symlinks permitted')
            if file.is_file():
                output.write(file, file.relative_to(folder))
    result = {'model': alias, 'directory_validated': True, 'agent_compiled': True,
              'agent_class': type(agent).__name__, 'tools': raw['tools'],
              'versions': {n: importlib.metadata.version(n) for n in ['adk-submission','adk-eval-core','swegemma','google-adk','litellm']},
              'archive': str(archive.relative_to(ROOT)), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'official_tasks_scored': False, 'local_python_harness_exported': False}
    target = (Path(report_root) if report_root is not None else ROOT / 'reports/official') / f'{key}-validation.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--model', choices=['12b','31b'], required=True)
    args = parser.parse_args()
    print(json.dumps(validate(ROOT/'submission_candidates'/args.model,args.model), indent=2))
