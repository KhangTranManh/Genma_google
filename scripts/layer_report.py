"""Controlled layer comparisons on 12B and 31B; prior cohort remains separate."""
import csv
import hashlib
import json
import tomllib
from progress_report import read, grade

LABELS = {'layers_control_v1': 'Đối chứng B', 'layers_prompt_v1': '1 · Prompt',
          'layers_code_v1': '2 · Code harness', 'layers_runtime_v1': '3 · Context runtime'}


def generate(root, spec_key='layer_comparison', labels=None, report_name='two-model-layers', baseline_id='layers_control_v1'):
    labels = LABELS if labels is None else labels
    with (root / 'configs/study.toml').open('rb') as stream:
        spec = tomllib.load(stream).get(spec_key)
    if not spec:
        return {'rows': [], 'warnings': [], 'assessments': []}
    rows = []
    warnings = []
    for path in sorted((root / 'runs').glob('*/manifest.json')):
        m = read(path)
        ident = m.get('experiment', {}).get('id')
        if ident not in spec['experiments']:
            continue
        agent = m.get('agent') or {}
        workflow = dict(m.get('workflow', {}))
        state = read(root / 'runs/pipeline' / ident / 'state.json')
        # Only the declared layer may differ; hashes of every other control must match.
        layer = (m.get('config', {}).get('ablation') or {}).get('layer')
        effective = dict(workflow)
        normalized_prompt = m.get('prompt_sha256')
        if layer == 'prompt':
            effective['system_prompt'] = 'experiments/prompts/tool_recovery_v1.md'
            normalized_prompt = hashlib.sha256((root / effective['system_prompt']).read_bytes()).hexdigest()
        elif layer == 'code':
            effective['progress_revision'] = 1
        elif layer == 'runtime':
            effective['history_char_limit'] = 12000
        controls = {'workflow': effective, 'prompt': normalized_prompt,
                    'source': m.get('workflow_sha256'), 'serving': m.get('config', {}).get('serving'),
                    'dataset': state.get('invariants', {}).get('dataset_sha256'),
                    'model': m.get('model'), 'commit': m.get('base_commit')}
        # Synthetic demo commits include fresh timestamps; frozen dataset identifies
        # their source content. Real-repository comparisons still require exact SHA.
        synthetic = m.get('instance_id') == 'demo-urlkit-query' and m.get('repo') == 'local/urlkit' and bool(controls['dataset'])
        if synthetic:
            controls['commit'] = {'synthetic_dataset_sha256': controls['dataset']}
        # system_prompt may be resolved absolutely in manifest: normalize representation.
        effective['system_prompt'] = normalized_prompt
        origin = agent.get('submission_origin')
        evaluation = grade(path.parent / 'evaluation.json')
        rows.append({'model': m.get('model_key'), 'experiment': ident, 'label': labels[ident],
                     'run_id': path.parent.name, 'base_commit': m.get('base_commit'), 'synthetic_dataset_identity': synthetic, 'status': m.get('status'), 'stop_reason': agent.get('reason'),
                     'submission_origin': origin, 'autonomous_pass': m.get('status') == 'local_pass' and origin == 'model' and bool(evaluation and evaluation['exit_code'] == 0),
                     'seconds': m.get('solve_elapsed_seconds'), 'turns': agent.get('turns'), 'tool_calls': agent.get('tool_calls'),
                     'input_tokens': agent.get('usage', {}).get('prompt_tokens'), 'output_tokens': agent.get('usage', {}).get('completion_tokens'),
                     'evaluation': evaluation, 'recovered_evaluation': grade(path.parent / 'recovered-evaluation.json'),
                     'control_sha256': hashlib.sha256(json.dumps(controls, sort_keys=True).encode()).hexdigest(),
                     'evidence': str(path.relative_to(root))})
        if m.get('code_changed_during_run'):
            warnings.append('Source changed during ' + path.parent.name)
    assessments = []
    for model in spec['models']:
        finished = [r for r in rows if r['model'] == model and r['status'] not in ('running', 'prepared')]
        if len({r['control_sha256'] for r in finished}) > 1:
            warnings.append(model + ': controls differ beyond declared layers; do not attribute gains until reviewed')
        baseline = [r for r in finished if r['experiment'] == baseline_id]
        for ident in spec['experiments'][1:]:
            candidates = [r for r in finished if r['experiment'] == ident]
            if not baseline or not candidates:
                assessments.append({'model': model, 'experiment': ident, 'finding': 'Chờ đủ cặp đối chứng/candidate.'})
                continue
            b, c = baseline[-1], candidates[-1]
            if b['control_sha256'] != c['control_sha256']:
                finding = 'Sai khác controls ngoài thiết kế; cần xem lại trước khi so sánh.'
            elif c['autonomous_pass'] and not b['autonomous_pass']:
                finding = 'Cải thiện tự hoàn tất trên lượt này; cần chạy lặp để xác nhận.'
            elif b['autonomous_pass'] and not c['autonomous_pass']:
                finding = 'Regression trên lượt này; chưa chấp nhận candidate.'
            elif b['autonomous_pass'] and c['autonomous_pass']:
                delta = c['seconds'] - b['seconds']
                finding = f'Cả hai tự submit và pass; thời gian candidate trừ baseline = {delta:+.1f}s. Một mẫu chưa chứng minh cải thiện ổn định.'
            else:
                finding = 'Chưa cải thiện tự hoàn tất trong cặp này; xem patch thu hồi và trajectory.'
            assessments.append({'model': model, 'experiment': ident, 'finding': finding})
    result = {'spec': spec, 'rows': rows, 'warnings': warnings, 'assessments': assessments,
              'identity_note': 'URLKit tạo commit mới mỗi lượt (timestamp khác). So khớp nội dung bằng dataset hash đã đóng băng; giữ SHA gốc trong từng record. Repo thực vẫn so SHA chính xác.'}
    folder = root / 'reports'; folder.mkdir(exist_ok=True)
    temporary = folder / (report_name + '.json.tmp');temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n');temporary.replace(folder / (report_name + '.json'))
    title = 'So sánh kết hợp code + prompt: 12B và 31B' if spec_key == 'combined_comparison' else 'So sánh từng lớp: 12B và 31B'
    description = 'Đối chứng code revision 2 + recovery prompt so với code revision 2 + completion prompt.' if spec_key == 'combined_comparison' else 'Đối chứng mới + ba nhánh độc lập.'
    lines = ['# ' + title, '', description + ' Tất cả dùng model tự submit, không bật harness nộp hộ.', '',
             '| Model | Nhánh | Kết quả | Tự submit + pass | Giây | Lượt | Tools |', '|---|---|---|---|---:|---:|---:|']
    for model in spec['models']:
        for ident in spec['experiments']:
            selected = [r for r in rows if r['model'] == model and r['experiment'] == ident]
            if not selected:
                lines.append(f'| {model} | {labels[ident]} | Chờ chạy | — | — | — | — |')
            for r in selected:
                lines.append(f"| {model} | {r['label']} | {r['status']} | {r['autonomous_pass']} | {r['seconds']} | {r['turns']} | {r['tool_calls']} |")
    lines += ['', result['identity_note'], '', '## Đánh giá theo cặp', ''] + [f"- {a['model']} / {labels[a['experiment']]}: {a['finding']}" for a in assessments]
    lines += ['', '## Bằng chứng', ''] + [f"- [{r['run_id']}](../{r['evidence']})" for r in rows]
    lines += ['', '## Kiểm tra thiết kế', ''] + (warnings or ['Chưa phát hiện sai khác ngoài thiết kế.'])
    (folder / (report_name + '.md')).write_text('\n'.join(lines) + '\n')
    with (folder / (report_name + '.csv')).open('w', newline='') as stream:
        columns = ['model', 'experiment', 'run_id', 'status', 'autonomous_pass', 'seconds', 'turns', 'tool_calls', 'input_tokens', 'output_tokens', 'submission_origin', 'stop_reason', 'evidence']
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    return result
