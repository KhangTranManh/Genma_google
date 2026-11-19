from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
if any(char in str(root) for char in ' \t\n%'):
    raise SystemExit('Unsupported project path')
(root / 'runs/pipeline/model_metrics_v1').mkdir(parents=True, exist_ok=True)
units = []
for name in ('gemma-lab-metrics.service', 'gemma-lab-metrics.timer'):
    path = Path('/etc/systemd/system') / name
    if path.exists() and name.endswith('.service') and str(root) not in path.read_text():
        raise SystemExit('Metrics service belongs to another project')
    path.write_text((root / 'deploy/systemd' / name).read_text().replace('@PROJECT_ROOT@', str(root)))
    units.append(str(path))
subprocess.run(['systemd-analyze', 'verify', *units], check=True)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'gemma-lab-metrics.timer'], check=True)
