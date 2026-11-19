from pathlib import Path
import subprocess
import json
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'runs/staged-v1').mkdir(parents=True,exist_ok=True)
state=ROOT/'runs/staged-v1/state.json'
if not state.exists():
    state.write_text(json.dumps({'status':'running','phase':'queued','experiment':'staged-workflow-v1','in_progress':False,'completed':[], 'waiting_for':'Reading v2 study must finish before GPU reuse'},indent=2)+'\n')
units=[]
for name in ['gemma-lab-staged.service','gemma-lab-staged.timer','gemma-lab-staged-watch.service','gemma-lab-staged-watch.timer']:
    target=Path('/etc/systemd/system')/name
    if target.exists() and name.endswith('.service') and str(ROOT) not in target.read_text():raise SystemExit('Service belongs to another project')
    target.write_text((ROOT/'deploy/systemd'/name).read_text().replace('@PROJECT_ROOT@',str(ROOT)));units.append(str(target))
subprocess.run(['systemd-analyze','verify',*units],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','gemma-lab-staged.timer','gemma-lab-staged-watch.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','gemma-lab-staged.service'],check=True)
