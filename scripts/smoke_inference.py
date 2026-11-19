"""Send a real coding prompt and retain response, timing and token usage."""
import argparse
import json
from pathlib import Path
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/v1')
parser.add_argument('--model', default='gemma-4-e4b-it-qat-w4a16-ct')
parser.add_argument('--output', type=Path, default=Path('runs/smoke.json'))
args = parser.parse_args()
body = {
    'model': args.model,
    'messages': [{'role': 'user', 'content': 'Write a Python function deduplicate(items) that preserves input order and supports unhashable items. Include two assert examples. Return only Python code.'}],
    'max_tokens': 512, 'temperature': 0,
    'chat_template_kwargs': {'enable_thinking': False},
}
request = urllib.request.Request(args.base_url + '/chat/completions',
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
start = time.monotonic()
with urllib.request.urlopen(request, timeout=300) as response:
    result = json.load(response)
elapsed = time.monotonic() - start
usage = result.get('usage', {})
record = {'elapsed_seconds': elapsed, 'completion_tokens_per_second_end_to_end':
          usage.get('completion_tokens', 0) / elapsed, 'request': body, 'response': result}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(record, indent=2, ensure_ascii=False))
if result['choices'][0]['finish_reason'] != 'stop':
    raise SystemExit('Generation did not finish naturally; inspect the saved output')
