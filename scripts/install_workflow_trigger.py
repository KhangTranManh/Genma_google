"""Install only the workflow-code trial units; never expose a Docker socket to candidates."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
if any(char in str(root) for char in ' \t\n%'):
    raise SystemExit('Unsupported project path')
(root / 'runs/pipeline/workflow_code_12b_v2').mkdir(parents=True, exist_ok=True)
units = []
for name in ('gemma-lab-workflow.service', 'gemma-lab-workflow.timer'):
    target = Path('/etc/systemd/system') / name
    if target.exists() and name.endswith('.service') and str(root) not in target.read_text():
        raise SystemExit('Existing workflow service belongs to another project')
    target.write_text((root / 'deploy/systemd' / name).read_text().replace('@PROJECT_ROOT@', str(root)))
    units.append(str(target))
subprocess.run(['systemd-analyze', 'verify', *units], check=True)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'gemma-lab-workflow.timer'], check=True)
subprocess.run(['systemctl', 'list-timers', 'gemma-lab-workflow.timer', '--no-pager'], check=True)
