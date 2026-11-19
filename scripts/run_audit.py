"""Post-run evidence checks and descriptive analysis; never changes agent inputs."""
from collections import Counter
import json


def generate(root, comparison):
    records = []
    for row in (comparison or {}).get('rows', []):
        if row['status'] in ('running', 'prepared', None):
            continue
        folder = root / 'runs' / row['run_id']
        warnings = []
        for name in ['manifest.json', 'trajectory.jsonl', 'system_prompt.md', 'workflow-files.json']:
            if not (folder / name).is_file():
                warnings.append('Thiếu bằng chứng: ' + name)
        if row['submission_origin'] and not row['evaluation']:
            warnings.append('Có nguồn submit nhưng thiếu kết quả test độc lập')
        if row['status'] == 'local_pass' and (not row['evaluation'] or row['evaluation']['exit_code'] != 0):
            warnings.append('Trạng thái pass không khớp kết quả chấm')
        calls = Counter()
        submit_attempts = 0
        malformed = 0
        failed_tools = 0
        path = folder / 'trajectory.jsonl'
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if event.get('event') == 'tool_call':
                    calls[(event.get('name'), event.get('raw_arguments', ''))] += 1
                    submit_attempts += event.get('name') == 'submit_patch'
                if event.get('event') == 'tool_result':
                    result = event.get('result') or {}
                    failed_tools += bool(result.get('error')) or result.get('exit_code', 0) not in (0, None)
        if malformed:
            warnings.append(f'{malformed} dòng trajectory không đọc được')
        for name in ['evaluation.json', 'recovered-evaluation.json']:
            path = folder / name
            if path.exists() and json.loads(path.read_text()).get('truncated'):
                warnings.append(name + ': output bị cắt; không suy ra tổng test khi thiếu dòng tổng kết')
        recovered = row.get('recovered_evaluation')
        if row['status'] == 'incomplete' and recovered and recovered.get('exit_code') == 0:
            finding = 'Patch thu hồi pass test độc lập nhưng agent chưa submit thành công; cần cải thiện bước kết thúc workflow.'
        elif row['status'] == 'local_pass':
            finding = 'Patch đã nộp vượt test độc lập; nguồn nộp: ' + str(row['submission_origin']) + '.'
        elif row['status'] == 'incomplete':
            finding = 'Chưa hoàn tất; nguyên nhân dừng: ' + str(row['stop_reason']) + '. Patch thu hồi chưa chứng minh sửa đúng.'
        else:
            finding = 'Kết quả: ' + str(row['status']) + '; xem bằng chứng trước khi kết luận.'
        records.append({'run_id': row['run_id'], 'model': row['model'], 'experiment': row['experiment'],
                        'finding': finding, 'warnings': warnings, 'submit_attempts': submit_attempts,
                        'repeated_identical_requests': sum(max(n - 1, 0) for n in calls.values()),
                        'failed_tool_results': failed_tools})
    value = {'note': 'Lặp request đếm theo tên + arguments nguyên văn trong log, khác bộ phát hiện lặp của harness.', 'runs': records}
    target = root / 'reports/run-audit.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(target)
    return value
