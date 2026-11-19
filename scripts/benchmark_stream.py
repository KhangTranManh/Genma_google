"""Bounded streaming latency/throughput check; retains all model output."""
import argparse
import json
from pathlib import Path
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/v1')
parser.add_argument('--model', default='gemma-4-e4b-it-qat-w4a16-ct')
parser.add_argument('--repeats', type=int, default=3)
parser.add_argument('--output', type=Path, default=Path('runs/stream-benchmark.json'))
args = parser.parse_args()
results = []
for iteration in range(args.repeats):
    payload = {'model': args.model, 'messages': [{'role': 'user', 'content':
        'Write a Python function deduplicate(items) that preserves input order and supports unhashable items. Include two assert examples. Return only Python code.'}],
        'max_tokens': 256, 'temperature': 0, 'stream': True,
        'stream_options': {'include_usage': True}, 'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request(args.base_url + '/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first = None
    last_content = None
    text = ''
    usage = {}
    finish = None
    with urllib.request.urlopen(request, timeout=300) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith('data: '):
                continue
            if line == 'data: [DONE]':
                break
            event = json.loads(line[6:])
            if 'error' in event:
                raise RuntimeError(event['error'])
            if event.get('usage'):
                usage = event['usage']
            for choice in event.get('choices', []):
                content = choice.get('delta', {}).get('content')
                if content:
                    now = time.perf_counter()
                    first = first or now
                    last_content = now
                    text += content
                if choice.get('finish_reason'):
                    finish = choice['finish_reason']
    elapsed = time.perf_counter() - start
    tokens = usage.get('completion_tokens', 0)
    decode_seconds = last_content - first if first and last_content else 0
    record = {'iteration': iteration + 1, 'elapsed_seconds': elapsed,
              'time_to_first_content_seconds': first - start if first else None,
              'end_to_end_tokens_per_second': tokens / elapsed,
              'approx_decode_tokens_per_second': (tokens - 1) / decode_seconds if tokens > 1 and decode_seconds > 0 else None,
              'usage': usage, 'finish_reason': finish, 'content': text}
    results.append(record)
    print(json.dumps({k: v for k, v in record.items() if k != 'content'}), flush=True)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({'model': args.model, 'results': results}, indent=2) + '\n')
if not all(r['finish_reason'] == 'stop' and r['content'] for r in results):
    raise SystemExit('Inspect truncated or empty model output')
