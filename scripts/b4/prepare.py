"""Build pinned per-task Docker images for B4 tasks (same recipe as scripts/official/prepare_pilot.py, any task in tasks.jsonl)."""
from pathlib import Path
import argparse,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]

def build(task_id):
    if not all(c.isalnum() or c in '_-' for c in task_id):raise ValueError('Invalid task id')
    tasks={json.loads(l)['instance_id']:json.loads(l) for l in (ROOT/'data/freshswe/tasks.jsonl').read_text().splitlines()}
    t=tasks[task_id];image='gemma-official-pilot:'+task_id.lower()
    if subprocess.run(['docker','image','inspect',image],capture_output=True).returncode==0:return image
    folder=ROOT/'runs/official-build'/task_id;folder.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'docker/official-pilot/Dockerfile',folder/'Dockerfile')
    shutil.copyfile(ROOT/'data/freshswe/locks'/f"{t['base_commit']}.txt",folder/'requirements.txt')
    r=subprocess.run(['docker','build','-q','-t',image,str(folder)],timeout=1200,capture_output=True,text=True)
    if r.returncode:
        # Fallback: install pins one by one without dependency resolution; skip unavailable pins. Preflight decides usability.
        d=(ROOT/'docker/official-pilot/Dockerfile').read_text().replace('RUN pip install --no-cache-dir -r /opt/pilot/requirements.txt',
          'RUN while read -r pin; do [ -n "$pin" ] && (pip install -q --no-cache-dir --no-deps "$pin" || echo "SKIPPED $pin" >> /opt/pilot/skipped.txt); done < /opt/pilot/requirements.txt; touch /opt/pilot/skipped.txt')
        (folder/'Dockerfile').write_text(d);(folder/'FALLBACK').write_text(r.stderr[-3000:])
        subprocess.run(['docker','build','-q','-t',image,str(folder)],check=True,timeout=2400)
    return image

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tasks',nargs='+')
    for t in p.parse_args().tasks:print(t,build(t),flush=True)
