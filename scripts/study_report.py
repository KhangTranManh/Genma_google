"""Report saved evidence by method without aggregating unrelated experiments."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tomllib


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def load_study(root):
    with (root / 'configs/study.toml').open('rb') as stream:
        return tomllib.load(stream)


def test_result(path):
    data = read_json(path)
    if not data:
        return None
    text = data.get('output', '')
    count = re.search(r'Ran (\d+) tests?', text)
    return {'exit_code': data.get('exit_code'), 'timed_out': data.get('timed_out', False),
            'tests': int(count[1]) if count else None,
            'passed': len(re.findall(r'^test_.* \.\.\. ok$', text, re.MULTILINE))}


def collect(root):
    plan = load_study(root)
    report = {'name': plan['name'], 'generated_at': datetime.now(timezone.utc).isoformat(),
              'controller': read_json(root / 'runs/study/state.json'), 'stages': [], 'legacy_runs': []}
    runs = []
    for path in sorted((root / 'runs').glob('*/manifest.json')):
        item = read_json(path)
        if not item:
            continue
        run = path.parent
        usage = (item.get('agent') or {}).get('usage', {})
        record = {'run_id': run.name, 'model': item.get('model_key'), 'status': item['status'],
                  'elapsed_seconds': item.get('elapsed_seconds'), 'agent': item.get('agent'),
                  'prompt_sha256': item.get('prompt_sha256'), 'workflow_sha256': item.get('workflow_sha256'),
                  'submission_origin': (item.get('agent') or {}).get('submission_origin'),
                  'recovered_evaluation': test_result(run / 'recovered-evaluation.json'),
                  'workflow_variant': item.get('workflow_variant'), 'variant_workflow_sha256': item.get('variant_workflow_sha256'),
                  'code_changed_during_run': item.get('code_changed_during_run'), 'error': item.get('error'),
                  'prompt_tokens': usage.get('prompt_tokens'), 'completion_tokens': usage.get('completion_tokens'),
                  'evaluation': test_result(run / 'evaluation.json'),
                  'evidence': str(path.relative_to(root)), 'experiment': item.get('experiment', {}).get('id', 'legacy_mixed')}
        runs.append(record)
    for stage in plan['stages']:
        item = dict(stage)
        item['state'] = read_json(root / 'runs/pipeline' / stage['id'] / 'state.json')
        item['runs'] = [run for run in runs if run['experiment'] == stage['id']]
        item['status'] = ('definition_only' if stage['mode'] == 'definition'
                          else item['state'].get('phase', 'not_started'))
        prompts = {run['prompt_sha256'] for run in item['runs'] if run['prompt_sha256']}
        workflows = {run['workflow_sha256'] for run in item['runs'] if run['workflow_sha256']}
        models = {run['model'] for run in item['runs']}
        violations = []
        if any(run['code_changed_during_run'] for run in item['runs']):
            violations.append('Workflow source changed during a run')
        if len(workflows) > 1:
            violations.append('Multiple workflow source hashes')
        if stage.get('profile') in ('model_sweep', 'model_31b_retry', 'model_e4b_control', 'progress_baseline', 'progress_guard', 'progress_finish') and len(prompts) > 1:
            violations.append('Model sweep contains different prompts')
        if stage['mode'] == 'workflow_experiment' and (len(models) > 1 or len(prompts) > 1):
            violations.append('Workflow trial changed the model or prompt')
        if stage.get('profile') in ('prompt_only', 'prompt_only_v2') and len(models) > 1:
            violations.append('Prompt experiment contains different models')
        item['comparison_violations'] = violations
        report['stages'].append(item)
    report['legacy_runs'] = [run for run in runs if run['experiment'] == 'legacy_mixed']
    return report


def render(report):
    controller = report['controller']
    lines = ['# Báo cáo thí nghiệm Gemma local', '',
             'Cập nhật UTC: ' + report['generated_at'], '',
             'Trạng thái điều phối: **' + controller.get('status', 'not_started') + '**.', '',
             'Các phương pháp được báo cáo riêng. Kết quả hiện dùng một issue tổng hợp URLKit;',
             'đây là kiểm tra workflow local, chưa phải điểm cuộc thi hay benchmark nhiều repository.', '']
    if controller.get('recovery_history'):
        entry = controller['recovery_history'][-1]
        lines += ['**Khôi phục:** ' + entry.get('old_experiment', '') + ' → ' + entry.get('new_experiment', '') + '.',
                  'Bản trước dừng do lỗi khởi động model; kết quả cũ được giữ nguyên.',
                  '[Chi tiết khôi phục](recovery-20261116.md)', '']
    names = {'model_sweep': 'Phần 1 — Đổi model, giữ prompt và workflow',
             'prompt_only': 'Phần 2 — Chỉ thay prompt, giữ model và workflow',
             'prompt_only_v2': 'Phần 2 — Chỉ thay prompt (v2 sau khi sửa chuyển model)',
             'workflow_code_v2': 'Phần 3 — Tự sửa code workflow trong container',
             'model_31b_retry': 'Chạy lại 31B và đối chứng 12B — ngân sách 900 giây',
             'model_e4b_control': 'Đối chứng E4B — cùng prompt và ngân sách 900 giây',
             'performance_metrics': 'Tốc độ sinh và VRAM — benchmark cố định',
             'progress_baseline': 'A — Đối chứng workflow cũ trên ba model',
             'progress_guard': 'B — Trạng thái và chống loop trên ba model',
             'progress_finish': 'C — Kết thúc có xác minh trên ba model',
             'layers_control': 'Hai model — đối chứng mới',
             'layers_prompt': 'Hai model — chỉ đổi prompt',
             'layers_code': 'Hai model — chỉ đổi code harness',
             'layers_runtime': 'Hai model — chỉ đổi cấu hình context runtime',
             'combined_control': 'Kết hợp — đối chứng code mới + prompt cũ',
             'combined_prompt': 'Kết hợp — code mới + prompt mới'}
    for stage in report['stages']:
        title = names.get(stage.get('profile'), 'Phần 3 — Định nghĩa tự sửa code workflow')
        lines += ['## ' + title, '', '**Trạng thái:** ' + stage['status'], '']
        if stage['mode'] == 'definition':
            lines += ['Đã định nghĩa phạm vi và quy trình kiểm chứng. Chưa thực thi model tự sửa code workflow;',
                      'không có số liệu thực nghiệm cho phần này.', '',
                      '[Tài liệu định nghĩa](../' + stage['definition'] + ')', '']
            continue
        if stage.get('profile') in ('model_31b_retry', 'model_e4b_control'):
            lines += ['Lượt bổ sung dùng cùng prompt hướng dẫn phục hồi lỗi tools, 900 giây, 48 lượt và 96 thao tác cho cả ba model.',
                      'Giữ nguyên workflow. Không so trực tiếp với ngân sách 240 giây và prompt cũ ở phần 1.', '']
        if stage['comparison_violations']:
            lines += ['**Không dùng để so sánh trực tiếp:** ' + '; '.join(stage['comparison_violations']), '']
        if not stage['runs']:
            lines += ['Chưa có lượt chạy được lưu.', '']
        else:
            lines += ['| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |',
                      '|---|---|---|---:|---:|---:|---|']
            for run in stage['runs']:
                evaluation = run['evaluation']
                verdict = 'chưa đánh giá'
                if evaluation:
                    verdict = (f"{evaluation['passed']}/{evaluation['tests']}"
                               if evaluation['tests'] is not None else f"exit={evaluation['exit_code']}")
                elapsed = '-' if run['elapsed_seconds'] is None else f"{run['elapsed_seconds']:.1f}"
                turns = (run.get('agent') or {}).get('turns', '-')
                lines.append(f"| [{run['run_id']}](../{run['evidence']}) | {run['model']}{' / ' + run['workflow_variant'] if run.get('workflow_variant') else ''} | {run['status']} | {elapsed} | {turns} | {run['completion_tokens']} | {verdict} |")
            lines.append('')
        state = stage['state']
        if state.get('decision'):
            lines += ['Quyết định candidate: **' + state['decision'] + '**. Workflow đang dùng chưa bị ghi đè.', '']
        if state.get('candidate_rejection'):
            lines += ['Candidate bị loại: `' + str(state['candidate_rejection']).replace('`', '') + '`.', '']
        if state.get('error'):
            lines += ['Lỗi ghi nhận: `' + str(state['error']).replace('`', '') + '`.', '']
        lines += ['State và hash cố định: [state.json](../runs/pipeline/' + stage['id'] + '/state.json).', '']
    lines += ['## Kết quả lịch sử', '',
              f"Đã giữ {len(report['legacy_runs'])} lượt `legacy_mixed` riêng. Những lượt này thay đổi nhiều yếu tố;",
              'không gộp vào kết luận của các thí nghiệm độc lập.', '',
              '[Bảng lịch sử](../experiments/RESULTS.md)', '',
              '## Giới hạn và bước tiếp theo', '',
              '- Không gộp điểm của các phương pháp hoặc suy ra tác dụng riêng từ lượt thay đổi nhiều yếu tố.',
              '- Một issue và một lần chạy mỗi cấu hình chưa đủ kết luận model hay phương pháp nào tốt hơn nói chung.',
              '- Tiếp theo cần tập issue cố định từ nhiều repo, chạy lặp và kiểm tra tương thích harness chính thức.',
              '- Phần tự sửa workflow dùng bản sao cách ly và đánh giá cặp; mọi cải thiện chỉ là kết quả sơ bộ trên bài mẫu.', '']
    lines += ['[Bảng so sánh đủ tiêu chí cho ba model](model-comparison.md)', '',
              '[So sánh A/B/C chống loop](anti-loop-comparison.md)', '']
    return '\n'.join(lines)


def generate(root):
    report = collect(root)
    folder = root / 'reports'
    folder.mkdir(exist_ok=True)
    write_json(folder / 'study-report.json', report)
    temporary = folder / 'study-report.md.tmp'
    temporary.write_text(render(report))
    temporary.replace(folder / 'study-report.md')
    from comparison_report import generate as comparison_generate
    comparison_generate(root)
    from progress_report import generate as progress_generate
    comparison = progress_generate(root)
    from run_audit import generate as audit_generate
    report["run_audit"] = audit_generate(root, comparison)
    from model_analysis import generate as analysis_generate
    report["model_size_analysis"] = analysis_generate(root, comparison, report["run_audit"])
    write_json(folder / "study-report.json", report)
    with (folder / "study-report.md").open("a") as output:
        output.write("\n\n" + (folder / "model-size-analysis.md").read_text())
    from layer_report import generate as layer_generate
    report["layer_comparison"] = layer_generate(root)
    report["combined_comparison"] = layer_generate(root, spec_key="combined_comparison",
        labels={"combined_control_v1": "Code mới + prompt cũ", "combined_prompt_v1": "Code mới + prompt mới"},
        report_name="two-model-combined", baseline_id="combined_control_v1")
    write_json(folder / "study-report.json", report)
    if (folder / "two-model-combined.md").exists():
        with (folder / "study-report.md").open("a") as output:
            output.write("\n\n" + (folder / "two-model-combined.md").read_text())
    from official.report import generate as official_generate
    report["official_pilot"] = official_generate(root)
    from html_report import generate as html_generate
    html_generate(root, report, comparison)
    return report

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    generate(root)
    print(root / 'reports/study-report.md')
