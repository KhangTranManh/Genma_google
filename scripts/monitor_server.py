"""Observe a running local server and append timestamped GPU/HTTP snapshots."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8000')
parser.add_argument('--duration', type=float, default=60)
parser.add_argument('--interval', type=float, default=5)
parser.add_argument('--output', type=Path, default=Path('runs/server-monitor.jsonl'))
args = parser.parse_args()
if args.interval <= 0 or args.duration <= 0:
    parser.error('duration and interval must be positive')
args.output.parent.mkdir(parents=True, exist_ok=True)
deadline = time.monotonic() + args.duration
with args.output.open('a') as output:
    while True:
        record = {'timestamp': datetime.now(timezone.utc).isoformat()}
        gpu = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu',
                              '--format=csv,noheader,nounits'], text=True, capture_output=True)
        record['gpu'] = gpu.stdout.strip().splitlines()
        try:
            with urllib.request.urlopen(args.url + '/health', timeout=5) as response:
                record['health'] = response.status
        except (OSError, urllib.error.URLError) as error:
            record['health_error'] = str(error)
        line = json.dumps(record)
        print(line, flush=True)
        output.write(line + '\n')
        output.flush()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(args.interval, remaining))
