from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'runs/reading-v1').mkdir(parents=True,exist_ok=True)
units=[]
for name in ['gemma-lab-reading.service','gemma-lab-reading.timer','gemma-lab-reading-watch.service','gemma-lab-reading-watch.timer']:
    target=Path('/etc/systemd/system')/name
    if target.exists() and name.endswith('.service') and str(ROOT) not in target.read_text():raise SystemExit('Service belongs to another project')
    target.write_text((ROOT/'deploy/systemd'/name).read_text().replace('@PROJECT_ROOT@',str(ROOT)));units.append(str(target))
subprocess.run(['systemd-analyze','verify',*units],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','gemma-lab-reading.timer','gemma-lab-reading-watch.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','gemma-lab-reading.service'],check=True)
