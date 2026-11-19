"""Build pinned per-task Docker environments without executing repository code on host."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--task', required=True)
    args = parser.parse_args()
    source = ROOT / 'data/freshswe'
    tasks = [json.loads(line) for line in (source/'pilot-tasks.jsonl').read_text().splitlines()]
    task = next(t for t in tasks if t['instance_id'] == args.task)
    name = task['instance_id']
    if not all(c.isalnum() or c in '_-' for c in name):
        raise ValueError('Invalid task id')
    image = 'gemma-official-pilot:' + name.lower()
    exists = subprocess.run(['docker', 'image', 'inspect', image], capture_output=True).returncode == 0
    if not exists:
        folder = ROOT/'runs/official-build'/name;folder.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'docker/official-pilot/Dockerfile',folder/'Dockerfile')
        shutil.copyfile(source/'locks'/f'{task["base_commit"]}.txt',folder/'requirements.txt')
        subprocess.run(['docker','build','-t',image,str(folder)],check=True,timeout=1200)
    print(image)


if __name__ == '__main__':
    main()
