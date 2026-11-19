"""One GPU model per trigger; bounded, identical streaming benchmark and GPU sampling."""
import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gemma_lab.config import load
from gemma_lab.experiments import invariants
from gemma_lab.provisioning import start_model
from gemma_lab.serving import endpoint
from study_report import write_json

PROMPT = 'Write a Python function deduplicate(items) that preserves input order and supports unhashable items. Include two assert examples. Return only Python code.'


def benchmark(base_url, alias, output_tokens):
    payload = {'model': alias, 'messages': [{'role': 'user', 'content': PROMPT}],
               'temperature': 0, 'max_tokens': output_tokens, 'min_tokens': output_tokens,
               'stream': True, 'stream_options': {'include_usage': True},
               'chat_template_kwargs': {'enable_thinking': False}}
    request = urllib.request.Request(base_url + '/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first = last = None
    text, usage, finish = '', {}, None
    with urllib.request.urlopen(request, timeout=90) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith('data: '):
                continue
            if line == 'data: [DONE]':
                break
            data = json.loads(line[6:])
            if data.get('error'):
                raise RuntimeError(data['error'])
            if data.get('usage'):
                usage = data['usage']
            for choice in data.get('choices', []):
                delta = choice.get('delta', {})
                content = delta.get('content') or delta.get('reasoning') or delta.get('reasoning_content')
                if content:
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    text += content
                finish = choice.get('finish_reason') or finish
    elapsed = time.perf_counter() - start
    tokens = usage.get('completion_tokens')
    if tokens != output_tokens or first is None:
        raise ValueError(f'Unexpected benchmark output: {tokens} tokens, expected {output_tokens}')
    return {'elapsed_seconds': elapsed, 'ttft_seconds': first - start,
            'end_to_end_tokens_per_second': tokens / elapsed,
            'approx_decode_tokens_per_second': (tokens - 1) / (last - first) if last > first else None,
            'usage': usage, 'finish_reason': finish, 'content': text}


def sample_gpu(stop, samples, interval, errors):
    while not stop.is_set():
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu',
                                     '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
        except Exception as error:
            errors.append(str(error))
            return
        if result.returncode:
            errors.append(result.stderr.strip() or 'nvidia-smi failed')
            return
        if result.returncode == 0:
            for row in csv.reader(result.stdout.splitlines()):
                samples.append({'timestamp': time.time(), 'index': int(row[0]), 'name': row[1].strip(),
                                'memory_used_mib': int(row[2]), 'memory_total_mib': int(row[3]), 'utilization_percent': int(row[4])})
        stop.wait(interval)


def summarize(trials, samples):
    if not trials or not samples:
        raise ValueError('Missing performance or GPU evidence')
    decode = [t['approx_decode_tokens_per_second'] for t in trials if t['approx_decode_tokens_per_second'] is not None]
    return {'repeats': len(trials),
            'median_end_to_end_tokens_per_second': statistics.median(t['end_to_end_tokens_per_second'] for t in trials),
            'median_ttft_ms': statistics.median(t['ttft_seconds'] for t in trials) * 1000,
            'median_approx_decode_tokens_per_second': statistics.median(decode) if decode else None,
            'sampled_max_memory_mib': {str(i): max(s['memory_used_mib'] for s in samples if s['index'] == i)
                                      for i in sorted({s['index'] for s in samples})}}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop-timer-on-terminal', action='store_true')
    args = parser.parse_args(argv)
    project = load(ROOT / 'configs/performance.toml')
    settings = project.raw['performance']
    folder = project.path('runs') / 'pipeline' / settings['id']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'state.json'
    if args.status:
        print(path.read_text() if path.exists() else 'Metrics not initialized')
        return 0
    with (project.path('runs') / 'pipeline/shared-worker.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another experiment is running; metrics deferred', flush=True)
            return 0
        control = invariants(project)
        control['benchmark_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        state = json.loads(path.read_text()) if path.exists() else {
            'phase': 'run', 'model_index': 0, 'results': {}, 'invariants': control}
        try:
            if state['phase'] in ('complete', 'needs_review'):
                return 0
            if state.get('in_progress') or state['invariants'] != control:
                raise ValueError('Metrics interrupted or controls changed; inspect before resuming')
            state['in_progress'] = True
            write_json(path, state)
            key = settings['model_order'][state['model_index']]
            _, model = project.select('model', key)
            start_model(project, key, model)
            samples, trials, stop, sampling_errors = [], [], threading.Event(), []
            sampler = threading.Thread(target=sample_gpu, args=(stop, samples, settings['sample_interval_seconds'], sampling_errors), daemon=True)
            sampler.start()
            try:
                # First request warms the exact benchmark shape; retain it but exclude it from medians.
                warmup = benchmark(endpoint(project), model['alias'], settings['output_tokens'])
                for _ in range(settings['repeats']):
                    trials.append(benchmark(endpoint(project), model['alias'], settings['output_tokens']))
            finally:
                stop.set()
                sampler.join(timeout=6)
            if sampling_errors or sampler.is_alive():
                raise RuntimeError('GPU sampling did not complete reliably: ' + str(sampling_errors))
            record = {'model': key, 'alias': model['alias'], 'prompt': PROMPT,
                      'output_tokens': settings['output_tokens'], 'warmup': warmup, 'trials': trials,
                      'gpu_samples': samples, 'summary': summarize(trials, samples),
                      'serving_config': project.raw['serving'], 'model_revision': model.get('revision'),
                      'sample_interval_seconds': settings['sample_interval_seconds'],
                      'measurement_scope': 'Fixed-length warmed streaming requests; VRAM sampled during benchmark only.'}
            write_json(folder / (key + '.json'), record)
            state['results'][key] = record['summary']
            state['model_index'] += 1
            if state['model_index'] >= len(settings['model_order']):
                state['phase'] = 'complete'
        except Exception as error:
            state.update(phase='needs_review', error=str(error))
        finally:
            state['in_progress'] = False
            state['updated_at'] = datetime.now(timezone.utc).isoformat()
            write_json(path, state)
            print(json.dumps(state, indent=2), flush=True)
            if state['phase'] in ('complete', 'needs_review') and args.stop_timer_on_terminal:
                subprocess.run(['systemctl', 'stop', 'gemma-lab-metrics.timer'], check=False)
        return 1 if state['phase'] == 'needs_review' else 0

if __name__ == '__main__':
    raise SystemExit(main())
