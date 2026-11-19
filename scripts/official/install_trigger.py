from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'runs/official-pilot').mkdir(parents=True,exist_ok=True)
paths=[]
for suffix in ['service','timer']:
    name='gemma-lab-official-pilot.'+suffix
    target=Path('/etc/systemd/system')/name
    if target.exists() and suffix=='service' and str(ROOT) not in target.read_text():
        raise SystemExit('Service belongs to another project')
    target.write_text((ROOT/'deploy/systemd'/name).read_text().replace('@PROJECT_ROOT@',str(ROOT)))
    paths.append(str(target))
subprocess.run(['systemd-analyze','verify',*paths],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','gemma-lab-official-pilot.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','gemma-lab-official-pilot.service'],check=True)
