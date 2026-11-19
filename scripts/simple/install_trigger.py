from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'runs/simple-v1').mkdir(parents=True,exist_ok=True)
units=[]
for name in ['gemma-lab-simple.service','gemma-lab-simple.timer','gemma-lab-simple-watch.service','gemma-lab-simple-watch.timer']:
    target=Path('/etc/systemd/system')/name
    if target.exists() and name.endswith('.service') and str(ROOT) not in target.read_text():raise SystemExit('Service belongs to another project')
    target.write_text((ROOT/'deploy/systemd'/name).read_text().replace('@PROJECT_ROOT@',str(ROOT)));units.append(str(target))
subprocess.run(['systemd-analyze','verify',*units],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','gemma-lab-simple.timer','gemma-lab-simple-watch.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','gemma-lab-simple.service'],check=True)
