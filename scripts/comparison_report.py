"""One matched three-model table with explicit task/performance provenance."""
import csv
import hashlib
import json
from pathlib import Path
import tomllib


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def protocol(manifest, state):
    serving = manifest.get('config', {}).get('serving', {})
    data = {'workflow_sha256': manifest.get('workflow_sha256'), 'prompt_sha256': manifest.get('prompt_sha256'),
            'workflow': manifest.get('workflow'), 'serving': serving,
            'dataset_sha256': state.get('invariants', {}).get('dataset_sha256')}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def task_row(root, path):
    manifest = read(path)
    run = path.parent
    experiment = manifest.get('experiment', {}).get('id')
    state = read(root / 'runs/pipeline' / experiment / 'state.json')
    agent = manifest.get('agent') or {}
    evaluation = read(run / 'evaluation.json')
    public = read(run / 'public-test-result.json')
    events = []
    trajectory = run / 'trajectory.jsonl'
    if trajectory.exists():
        for line in trajectory.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    edit_errors = sum(event['event'] == 'tool_result' and event.get('name') == 'edit_file'
                      and bool(event.get('result', {}).get('error')) for event in events)
    import re
    count = re.search(r'Ran (\d+) tests?', evaluation.get('output', ''))
    passed = len(re.findall(r'^test_.* \.\.\. ok$', evaluation.get('output', ''), re.MULTILINE))
    return {'model': manifest.get('model_key'), 'run_id': run.name, 'experiment': experiment,
            'status': manifest['status'], 'submitted': agent.get('reason') in ('submitted', 'harness_submitted') and (run / 'patch.diff').exists(),
            'public_test_passed': public.get('exit_code') == 0 if public else None,
            'independent_tests_passed': passed if evaluation else None,
            'independent_tests_total': int(count[1]) if count else None,
            'elapsed_seconds': manifest.get('elapsed_seconds'), 'turns': agent.get('turns'), 'tool_calls': agent.get('tool_calls'),
            'prompt_tokens': agent.get('usage', {}).get('prompt_tokens'),
            'completion_tokens': agent.get('usage', {}).get('completion_tokens'), 'edit_errors': edit_errors,
            'stop_reason': agent.get('reason'), 'error': manifest.get('error'),
            'protocol_sha256': protocol(manifest, state), 'workflow_sha256': manifest.get('workflow_sha256'),
            'prompt_sha256': manifest.get('prompt_sha256'), 'code_changed_during_run': manifest.get('code_changed_during_run'),
            'evidence': str(path.relative_to(root))}


def generate(root):
    plan_path = root / 'configs/study.toml'
    with plan_path.open('rb') as stream:
        plan = tomllib.load(stream)
    comparison = plan.get('comparison')
    if not comparison:
        return
    rows = []
    for path in sorted((root / 'runs').glob('*/manifest.json')):
        manifest = read(path)
        if manifest.get('experiment', {}).get('id') in comparison['experiments']:
            rows.append(task_row(root, path))
    metrics = read(root / 'runs/pipeline' / comparison['metrics'] / 'state.json')
    for row in rows:
        row['performance'] = metrics.get('results', {}).get(row['model'])
        perf = row['performance'] or {}
        row['benchmark_tokens_per_second'] = perf.get('median_end_to_end_tokens_per_second')
        row['benchmark_ttft_ms'] = perf.get('median_ttft_ms')
        row['benchmark_vram_gpu0_mib'] = perf.get('sampled_max_memory_mib', {}).get('0')
        row['benchmark_vram_gpu1_mib'] = perf.get('sampled_max_memory_mib', {}).get('1')
    completed = [row for row in rows if row['status'] not in ('running', 'prepared')]
    warnings = []
    if len({row['protocol_sha256'] for row in completed}) > 1:
        warnings.append('Các lượt task có protocol khác nhau; chưa được xếp hạng chung.')
    if any(row['code_changed_during_run'] for row in completed):
        warnings.append('Workflow đã thay đổi trong một lượt chạy.')
    report = {'comparison': comparison, 'rows': rows, 'metrics_phase': metrics.get('phase', 'not_started'),
              'comparison_warnings': warnings,
              'scope': 'One synthetic task per model. Performance uses a separate fixed-length streaming benchmark.'}
    folder = root / 'reports'
    folder.mkdir(exist_ok=True)
    temporary = folder / 'model-comparison.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(folder / 'model-comparison.json')
    lines = ['# Bảng so sánh E4B, 12B và 31B', '',
             'Đợt đối chứng mới: cùng workflow, prompt phục hồi lỗi tools, issue URLKit và giới hạn **900 giây / 48 lượt / 96 thao tác**.',
             'Không trộn với các lượt 240 giây hoặc prompt cũ. Đây chưa phải benchmark nhiều repo hay điểm thi.', '']
    if warnings:
        lines += ['**Cần kiểm tra:** ' + '; '.join(warnings), '']
    lines += ['| Model | Trạng thái | Nộp patch | Test công khai | Test độc lập | Giây | Lượt / tools | Input / output tokens | Lỗi edit | Benchmark token/s | TTFT ms | VRAM GPU0 / GPU1 MiB |',
              '|---|---|---|---|---|---:|---|---|---:|---:|---:|---|']
    def cell(value):
        return '-' if value is None else str(value)
    for model in comparison['models']:
        items = [row for row in rows if row['model'] == model]
        if not items:
            lines.append(f'| {model} | chờ chạy | - | - | - | - | - | - | - | - | - | - |')
            continue
        for row in items:
            perf = row['performance'] or {}
            memory = perf.get('sampled_max_memory_mib', {})
            passed = row['independent_tests_passed']
            tests = '-' if passed is None else f"{passed}/{cell(row['independent_tests_total'])}"
            elapsed = '-' if row['elapsed_seconds'] is None else f"{row['elapsed_seconds']:.1f}"
            speed = '-' if not perf else f"{perf['median_end_to_end_tokens_per_second']:.1f}"
            ttft = '-' if not perf else f"{perf['median_ttft_ms']:.1f}"
            public = '-' if row['public_test_passed'] is None else ('pass' if row['public_test_passed'] else 'fail')
            lines.append(f"| {model} | {row['status']} | {'có' if row['submitted'] else 'chưa'} | {public} | {tests} | {elapsed} | {cell(row['turns'])} / {cell(row['tool_calls'])} | {cell(row['prompt_tokens'])} / {cell(row['completion_tokens'])} | {row['edit_errors']} | {speed} | {ttft} | {cell(memory.get('0'))} / {cell(memory.get('1'))} |")
    lines += ['', '## Cách đọc tiêu chí', '',
              '- Nộp patch và test độc lập quyết định việc giải được bài mẫu; lượt fail, hết lượt hoặc timeout vẫn được giữ.',
              '- Test công khai là kết quả bộ test trong repo. Test độc lập chạy trên bản sạch, ngoài context agent.',
              '- Lỗi edit chỉ đếm thao tác edit_file bị từ chối; lỗi test lúc tái hiện bug không bị tính là lỗi edit.',
              '- Benchmark tốc độ: một lượt warm-up rồi ba lượt cố định 128 output token, temperature 0, thinking tắt.',
              '- TTFT là thời gian tới chunk nội dung/reasoning đầu tiên. Tốc độ là median end-to-end token/s của benchmark ngắn, không phải tốc độ toàn task.',
              '- VRAM là mức lớn nhất được lấy mẫu trong benchmark, không phải peak của toàn lượt giải issue.',
              '- Dấu “-” nghĩa là chưa có dữ liệu hoặc chưa tới bước đánh giá; không có nghĩa là đạt.',
              '- Một issue và một lượt task mỗi model chưa đủ chứng minh ưu thế tổng quát.', '', '## Bằng chứng', '']
    for row in rows:
        lines.append(f"- {row['model']}: [manifest](../{row['evidence']}), dừng vì `{row['stop_reason']}`.")
    lines += ['', 'Trạng thái đo hiệu năng: **' + report['metrics_phase'] + '**.', '']
    temporary = folder / 'model-comparison.md.tmp'
    temporary.write_text('\n'.join(lines))
    temporary.replace(folder / 'model-comparison.md')
    columns = ['model', 'status', 'submitted', 'public_test_passed', 'independent_tests_passed',
               'independent_tests_total', 'elapsed_seconds', 'turns', 'tool_calls', 'prompt_tokens', 'completion_tokens',
               'edit_errors', 'stop_reason', 'benchmark_tokens_per_second', 'benchmark_ttft_ms',
               'benchmark_vram_gpu0_mib', 'benchmark_vram_gpu1_mib', 'protocol_sha256', 'evidence']
    with (folder / 'model-comparison.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    return report

if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[1])
