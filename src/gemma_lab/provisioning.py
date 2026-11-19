"""Pinned public checkpoints and a separately supervised vLLM service."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import urllib.request
from .serving import health
from .runs import write_json


def download(project, model):
    from huggingface_hub import snapshot_download
    target = (project.root / model['path']).resolve()
    metadata_url = f"https://huggingface.co/api/models/{model['repository']}/tree/{model['revision']}?recursive=true"
    with urllib.request.urlopen(metadata_url, timeout=30) as response:
        entries = json.load(response)
    wanted = [entry for entry in entries if entry.get('type') == 'file'
              and entry['path'].endswith(('.json', '.jinja', '.safetensors', '.model'))]
    provenance = target / 'source.json'
    if provenance.is_file():
        existing = json.loads(provenance.read_text())
        if existing.get('repo') == model['repository'] and existing.get('revision') == model['revision'] and all(
            (target / entry['path']).is_file() and (target / entry['path']).stat().st_size == entry['size']
            for entry in wanted
        ):
            print(f"Reusing pinned checkpoint: {target}", flush=True)
            return
    expected = sum(entry.get('size', 0) for entry in wanted)
    if shutil.disk_usage(project.root).free < expected * 2:
        raise ValueError('Not enough free disk space for checkpoint and temporary download data')
    snapshot_download(model['repository'], revision=model['revision'], local_dir=target,
                      token=False, max_workers=8,
                      allow_patterns=['*.json', '*.jinja', '*.safetensors', '*.model'])
    for entry in wanted:
        path = target / entry['path']
        if not path.is_file() or path.stat().st_size != entry['size']:
            raise ValueError(f"Checkpoint size mismatch: {entry['path']}")
    write_json(target / 'source.json', {'repo': model['repository'], 'revision': model['revision'],
                                      'verified_file_sizes': True})


def stop_manual_server(project):
    pidfile = project.path('runs') / 'vllm-server.pid'
    if not pidfile.is_file():
        return
    pid = int(pidfile.read_text().strip())
    proc = Path(f'/proc/{pid}/cmdline')
    if not proc.exists():
        return
    command = proc.read_bytes().replace(b'\0', b' ').decode()
    if not command:
        return
    if str(project.root / '.venv/bin/vllm') not in command or ' serve ' not in command or os.getpgid(pid) != pid:
        raise ValueError('Recorded server PID does not match a project-owned vLLM process')
    os.killpg(pid, signal.SIGTERM)
    for _ in range(30):
        if not proc.exists() or not proc.read_bytes():
            return
        time.sleep(0.5)
    os.killpg(pid, signal.SIGKILL)


def start_model(project, key, model):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', key):
        raise ValueError('Invalid model key for systemd instance')
    try:
        health(project, model)
        return
    except (OSError, ValueError):
        pass
    stop_manual_server(project)
    # A profile can select only 12B while another managed model still owns the port.
    for name in project.raw['models']:
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
            raise ValueError('Invalid model key')
        subprocess.run(['systemctl', 'stop', f'gemma-lab-vllm@{name}.service'], check=True)
    subprocess.run(['systemctl', 'start', f'gemma-lab-vllm@{key}.service'], check=True)
    until = time.monotonic() + project.raw['automation']['startup_timeout_seconds']
    while time.monotonic() < until:
        try:
            health(project, model)
            return
        except (OSError, ValueError):
            pass
        state = subprocess.run(['systemctl', 'is-failed', f'gemma-lab-vllm@{key}.service'], capture_output=True, text=True)
        if state.stdout.strip() == 'failed':
            raise RuntimeError(f'vLLM {key} failed to start; inspect runs/vllm-{key}.log')
        time.sleep(2)
    subprocess.run(['systemctl', 'stop', f'gemma-lab-vllm@{key}.service'], check=True)
    raise RuntimeError(f'vLLM {key} startup timed out')
