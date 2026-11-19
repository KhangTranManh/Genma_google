"""Serve both models at the same 16k context with an isolated service namespace."""
from pathlib import Path
import json
import re
import subprocess
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from gemma_lab.config import load


def start(model):
    if model not in ('12b','31b'):raise ValueError('Unsupported model')
    project=load(ROOT/'configs/reading-runtime-v2.toml');alias=project.raw['models'][model]['alias']
    def ready():
        try:
            d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/models',timeout=5))
            return any(x.get('id')==alias and x.get('max_model_len')==16384 for x in d['data'])
        except (OSError,ValueError,KeyError):return False
    if ready():return
    for name in project.raw['models']:
        if not re.fullmatch('[a-zA-Z0-9_-]+',name):raise ValueError('Unsafe service key')
        for prefix in ['gemma-lab-vllm@','gemma-lab-reading-v2-vllm@']:
            subprocess.run(['systemctl','stop',prefix+name+'.service'],check=True)
    subprocess.run(['systemctl','start',f'gemma-lab-reading-v2-vllm@{model}.service'],check=True)
    until=time.monotonic()+600
    while time.monotonic()<until:
        if ready():return
        status=subprocess.run(['systemctl','is-failed',f'gemma-lab-reading-v2-vllm@{model}.service'],capture_output=True,text=True)
        if status.stdout.strip()=='failed':raise RuntimeError('v2 model service failed; inspect v2 server log')
        time.sleep(2)
    raise RuntimeError('v2 model readiness timeout')

if __name__=='__main__':start(sys.argv[1])
