from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
(ROOT/'runs/reading-v2').mkdir(parents=True,exist_ok=True)
units=[]
for name in ['gemma-lab-reading.service','gemma-lab-reading.timer','gemma-lab-reading-watch.service','gemma-lab-reading-watch.timer']:
    text=(ROOT/'deploy/systemd'/name).read_text()
    text=text.replace('gemma-lab-reading','gemma-lab-reading-v2').replace('runs/reading-v1','runs/reading-v2')
    text=text.replace('scripts/official/reading_worker.py','scripts/official/reading_worker_v2.py')
    if 'reading_watch.py' in text:text=text.replace('scripts/official/reading_watch.py','scripts/official/reading_watch.py --version v2')
    target=Path('/etc/systemd/system')/name.replace('gemma-lab-reading','gemma-lab-reading-v2')
    target.write_text(text.replace('@PROJECT_ROOT@',str(ROOT)));units.append(str(target))
subprocess.run(['systemd-analyze','verify',*units],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','gemma-lab-reading-v2.timer','gemma-lab-reading-v2-watch.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','gemma-lab-reading-v2.service'],check=True)
