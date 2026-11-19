"""Paired policy ablation: separate autonomous, harness-assisted and recovered outcomes."""
import csv
import hashlib
import json
from pathlib import Path
import re
import tomllib


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def grade(path):
    data = read(path)
    if not data:
        return None
    output = data.get('output', '')
    total = re.search(r'Ran (\d+) tests?', output)
    return {'passed': len(re.findall(r'^test_.* \.\.\. ok$', output, re.MULTILINE)),
            'total': int(total[1]) if total else None, 'exit_code': data.get('exit_code'), 'error': data.get('error')}


def generate(root):
    with (root / 'configs/study.toml').open('rb') as stream:
        plan = tomllib.load(stream)
    spec = plan.get('progress_comparison')
    if not spec:
        return
    rows = []
    for path in sorted((root / 'runs').glob('*/manifest.json')):
        manifest = read(path)
        experiment = manifest.get('experiment', {}).get('id')
        if experiment not in spec['experiments']:
            continue
        run = path.parent
        settings = dict(manifest.get('workflow', {}))
        policy = settings.pop('agent_policy', 'baseline')
        mode = settings.pop('progress_mode', 'off')
        agent = manifest.get('agent') or {}
        state = read(root / 'runs/pipeline' / experiment / 'state.json')
        controls = {'workflow_sha256': manifest.get('workflow_sha256'), 'prompt_sha256': manifest.get('prompt_sha256'),
                    'settings': settings, 'serving': manifest.get('config', {}).get('serving'),
                    'dataset_sha256': state.get('invariants', {}).get('dataset_sha256')}
        rows.append({'run_id': run.name, 'experiment': experiment, 'model': manifest.get('model_key'),
            'policy': policy, 'mode': mode, 'status': manifest.get('status'), 'stop_reason': agent.get('reason'),
            'submission_origin': agent.get('submission_origin') or ('model' if agent.get('reason') == 'submitted' else None),
            'seconds': manifest.get('solve_elapsed_seconds', manifest.get('elapsed_seconds')), 'turns': agent.get('turns'),
            'tool_calls': agent.get('tool_calls'), 'output_tokens': agent.get('usage', {}).get('completion_tokens'),
            'progress': agent.get('progress'), 'blocked_repeats': (agent.get('progress') or {}).get('blocked_repeats_total', 0), 'evaluation': grade(run / 'evaluation.json'),
            'recovered_evaluation': grade(run / 'recovered-evaluation.json'),
            'code_changed_during_run': manifest.get('code_changed_during_run'),
            'control_sha256': hashlib.sha256(json.dumps(controls, sort_keys=True).encode()).hexdigest(),
            'evidence': str(path.relative_to(root))})
    warnings = []
    complete = [row for row in rows if row['status'] not in ('running', 'prepared')]
    if len({row['control_sha256'] for row in complete}) > 1:
        warnings.append('Frozen controls differ beyond the intended policy/mode flags; inspect before drawing a comparison.')
    if any(row['code_changed_during_run'] for row in complete):
        warnings.append('A workflow source changed during a run.')
    folder = root / 'reports'
    folder.mkdir(exist_ok=True)
    (folder / 'anti-loop-comparison.json').write_text(json.dumps({'spec': spec, 'rows': rows, 'warnings': warnings}, indent=2) + '\n')
    labels = {'progress_baseline_v1': 'A: đối chứng', 'progress_guard_v1': 'B: chống lặp', 'progress_finish_v1': 'C: chốt có xác minh'}
    lines = ['# So sánh chống loop trên ba model', '',
             'Giữ cùng system prompt, issue, test độc lập, vLLM và giới hạn 900 giây / 48 lượt / 96 thao tác.',
             'A dùng AgentLoop cũ. B thêm trạng thái và phát hiện lặp. C thêm xác minh và bước nộp do harness điều phối.', '',
             '## Trạng thái từng phần', '']
    for ident in spec['experiments']:
        state = read(root / 'runs/pipeline' / ident / 'state.json')
        lines.append('- ' + labels[ident] + ': **' + state.get('phase', 'chưa bắt đầu') + '**.')
    if warnings:
        lines += ['', '**Cần xem lại:** ' + '; '.join(warnings)]
    lines += ['', '| Model | Cấu hình | Kết quả | Test độc lập | Giây | Lượt / tools | Output tokens | Lặp bị chặn | Nguồn nộp | Patch thu hồi |',
              '|---|---|---|---|---:|---|---:|---:|---|---|']
    for model in spec['models']:
        for ident in spec['experiments']:
            items = [row for row in rows if row['model'] == model and row['experiment'] == ident]
            if not items:
                lines.append(f'| {model} | {labels[ident]} | chờ chạy | - | - | - | - | - | - | - |')
            for row in items:
                evaluation, recovered = row['evaluation'], row['recovered_evaluation']
                score = '-' if not evaluation else (f"{evaluation['passed']}/{evaluation['total']}" if evaluation['total'] is not None else f"exit={evaluation['exit_code']}")
                salvage = '-' if not recovered else ('pass (chỉ chẩn đoán)' if recovered['exit_code'] == 0 else 'fail / lỗi')
                seconds = '-' if row['seconds'] is None else f"{row['seconds']:.1f}"
                lines.append(f"| {model} | {labels[ident]} | {row['status']} | {score} | {seconds} | {row['turns']} / {row['tool_calls']} | {row['output_tokens']} | {row['blocked_repeats']} | {row['submission_origin'] or '-'} | {salvage} |")
    lines += ['', '## Quy ước', '',
              '- `model`: model gọi submit_patch; `harness`: bộ điều phối chốt sau kiểm tra trên đúng code version.',
              '- Patch thu hồi được chấm riêng sau khi dừng, không tính thành nộp patch thành công.',
              '- Test độc lập chỉ chạy sau khi kết thúc và không được đưa lại cho agent.',
              '- Code đổi sẽ vô hiệu hóa kết quả test cũ. Lượt test đã pass không được dùng cho code version mới.',
              '- Thời gian task gồm quan sát trạng thái và kiểm tra của harness; không dùng thời gian chấm patch thu hồi để đánh giá hiệu suất agent.',
              '- C là chế độ hỗ trợ nộp của harness local, chưa chứng minh model tự nộp được trong runtime chính thức.',
              '- Một issue mỗi cấu hình là thử nghiệm tích hợp, chưa đủ kết luận hiệu quả trên repo thực tế.', '', '## Bằng chứng', '']
    lines += [f"- {row['model']} / {labels[row['experiment']]}: [manifest](../{row['evidence']})" for row in rows]
    (folder / 'anti-loop-comparison.md').write_text('\n'.join(lines) + '\n')
    columns = ['model', 'experiment', 'policy', 'mode', 'status', 'stop_reason', 'submission_origin', 'seconds',
               'turns', 'tool_calls', 'output_tokens', 'blocked_repeats', 'control_sha256', 'evidence']
    with (folder / 'anti-loop-comparison.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)
    return {'rows': rows, 'warnings': warnings}
