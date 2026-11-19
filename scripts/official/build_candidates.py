"""Build declarative candidates; no local AgentLoop code is exported."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', choices=['recovery', 'completion'], default='completion')
    args = parser.parse_args()
    source = ROOT / 'experiments/prompts' / ('completion_contract_v1.md' if args.prompt == 'completion' else 'tool_recovery_v1.md')
    for key in ['12b', '31b']:
        folder = ROOT / 'submission_candidates' / key
        (folder / 'prompts').mkdir(parents=True, exist_ok=True)
        (folder / 'configs').mkdir(exist_ok=True)
        (folder / 'prompts/system.md').write_bytes(source.read_bytes())
        (folder / 'configs/sampling.yaml').write_text('temperature: 0\nmax_output_tokens: 2048\nthinking_config:\n  thinking_budget: 0\n  include_thoughts: false\n')
        model = f'gemma-4-{key}-it-qat-w4a16-ct'
        (folder / 'agent.yaml').write_text(f'''agent_class: LlmAgent
name: repo_coder
model: {model}
instruction: !include prompts/system.md
generate_content_config: !include configs/sampling.yaml
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
''')
        (folder / 'eval_config.yaml').write_text('evaluation:\n  timeout_seconds: 60\n  verification_timeout_seconds: 300\n  max_time_minutes: 15\n  max_tool_calls: 96\n  max_turns: 48\n')
        provenance = {'model': model, 'prompt_source': str(source.relative_to(ROOT)),
                      'prompt_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                      'local_progress_agent_exported': False, 'runtime': 'organizer ADK compiler and swegemma',
                      'status': 'requires compiler validation and task evaluation'}
        output = ROOT / 'reports/official';output.mkdir(parents=True, exist_ok=True)
        (output / f'{key}-candidate.json').write_text(json.dumps(provenance, indent=2) + '\n')
        print(folder)


if __name__ == '__main__':
    main()
