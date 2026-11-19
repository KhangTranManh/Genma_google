"""Install the timer for exactly one selected experiment profile."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from gemma_lab.config import load
from gemma_lab.worker import state_path

parser = argparse.ArgumentParser()
parser.add_argument('--experiment', choices=['legacy', 'model_sweep', 'prompt_only', 'prompt_only_v2', 'model_31b_retry', 'model_e4b_control', 'progress_baseline', 'progress_guard', 'progress_finish', 'layers_control', 'layers_prompt', 'layers_code', 'layers_runtime', 'combined_control', 'combined_prompt'], default='legacy')
parser.add_argument('--interval-seconds', type=int, default=300)
args = parser.parse_args()
if not 15 <= args.interval_seconds <= 3600:
    parser.error('interval-seconds must be between 15 and 3600')
if any(char in str(root) for char in ' \t\n%'):
    raise SystemExit('Installer requires a project path without whitespace or systemd specifiers')
config = root / ('configs/project.toml' if args.experiment == 'legacy'
                 else f'configs/experiments/{args.experiment}.toml')
project = load(config)
folder = state_path(project).parent
folder.mkdir(parents=True, exist_ok=True)
state = subprocess.run(['systemctl', 'show', 'gemma-lab-worker.service', '--property=ActiveState', '--value'],
                       text=True, capture_output=True, check=True).stdout.strip()
if state in ('active', 'activating', 'deactivating', 'reloading'):
    raise SystemExit('Wait for the current worker to finish before switching experiments')
subprocess.run(['systemctl', 'stop', 'gemma-lab-worker.timer'], check=True)
units = []
for name in ('gemma-lab-worker.service', 'gemma-lab-worker.timer', 'gemma-lab-vllm@.service'):
    source = root / 'deploy/systemd' / name
    content = (source.read_text().replace('@PROJECT_ROOT@', str(root))
               .replace('@WORKER_CONFIG@', str(config)).replace('@WORKER_LOG@', str(folder / 'worker.log')))
    if name == 'gemma-lab-worker.timer' and args.interval_seconds != 300:
        content = content.replace('OnUnitInactiveSec=5min', f'OnUnitInactiveSec={args.interval_seconds}s').replace('OnActiveSec=2min', 'OnActiveSec=15s')
    target = Path('/etc/systemd/system') / source.name
    if target.exists() and source.name != 'gemma-lab-worker.timer' and str(root) not in target.read_text():
        raise SystemExit(f'Existing unit belongs to a different installation: {target}')
    target.write_text(content)
    units.append(str(target))
subprocess.run(['systemd-analyze', 'verify', *units], check=True)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'gemma-lab-worker.timer'], check=True)
marker = root / 'runs/pipeline/active-experiment.json'
marker.write_text(json.dumps({'profile': args.experiment, 'config': str(config.relative_to(root)),
                              'state': str(state_path(project).relative_to(root)),
                              'selected_at': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
print('Selected experiment:', args.experiment, flush=True)
print('State:', state_path(project), flush=True)
subprocess.run(['systemctl', 'list-timers', 'gemma-lab-worker.timer', '--no-pager'], check=True)
