"""Render official-library integration and independent pilot evidence, with explicit scope."""
from datetime import datetime,timezone
from html import escape
from collections import Counter
import re
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def read(path):
    try:return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError):return {}


def generate(root=ROOT):
    folder=root/'reports/official';folder.mkdir(parents=True,exist_ok=True)
    state=read(root/'runs/official-pilot/state.json')
    tasks=['w3lib_264','packaging_1125','platformdirs_540']
    preflight=[dict(task=task,**{k:v for k,v in read(root/'runs/official-pilot/preflight'/task/'summary.json').items() if k!='task'}) for task in tasks]
    validations={model:read(folder/f'{model}-validation.json') for model in ['12b','31b']}
    rows=[]
    for model in ['12b','31b']:
        for task in tasks:
            path=root/'runs/official-pilot'/model/task/'summary.json'
            d=read(path)
            trace_paths=list((path.parent/'traces').glob('*.json'))
            trace=read(trace_paths[0]) if trace_paths else {}
            counts=Counter(call.get('function_name','unknown') for step in trace.get('steps',[]) for call in step.get('tool_calls',[]))
            outcomes=re.findall(r'(\d+) (failed|passed|errors?|skipped)', d.get('test_output',''))
            patch=path.parent/'agent.patch'
            rows.append({'model':model,'task':task,'status':('pass' if d.get('resolved') else 'fail') if d else 'pending',
                         'seconds':d.get('duration_seconds'),'tools':d.get('tool_calls'), 'llm_calls':d.get('total_llm_calls'),
                         'tool_requests_by_name':dict(counts), 'submit_requests':counts.get('submit_patch',0),
                         'patch_bytes':patch.stat().st_size if patch.exists() else None,
                         'observed_test_summary':outcomes[-4:],
                         'error':d.get('error_message') or d.get('error'),'evidence':str(path.relative_to(root)) if d else None})
    record={'generated_at':datetime.now(timezone.utc).isoformat(),'state':state,'validations':validations,'preflight':preflight,'rows':rows,
            'scope':'Official public wheelhouse v31 compiler/evaluator with independent FreshSWE-Py tasks; not Kaggle competition score.',
            'differences':['2 A16 GPUs / vLLM 0.33.0 / 8192 context, not official 4 L4 / wheelhouse vLLM / 32768 context',
                           'Host dependencies resolved locally; organizer core wheels and ADK version pinned, not a full wheelhouse recreation',
                           'Local ProgressAgent and its verification fix are not used by the official runtime',
                           'Three public issue-sourced tasks selected before model outcomes; not a representative score estimate']}
    completed=[r for r in rows if r['status']!='pending']
    analysis=[]
    if completed:
        analysis.append(f"Đã kết thúc {len(completed)}/6 lượt; thành công {sum(r['status']=='pass' for r in completed)} lượt. Đây là pilot ba issue/model, không phải ước lượng điểm leaderboard.")
        analysis.append(f"{sum('turns budget' in (r['error'] or '') for r in completed)}/{len(completed)} lượt chạm giới hạn 48 lượt. Thời gian ngắn hơn 900 giây không có nghĩa còn lượt để thử tiếp.")
        analysis.append('w3lib: patch của cả hai model chưa xử lý được test hiệu năng về catastrophic backtracking; chấm độc lập ghi 67 pass / 1 fail. packaging: cả hai không có patch thu hồi, nên không ghi 0 test pass như một kết quả đã chạy test.')
        analysis.append('Các request read_file chiếm phần lớn lượt ở 31B; một số filepath bị ghép sai với start_line. Đây là triệu chứng từ trajectory, chưa chứng minh do model, prompt hay parser riêng lẻ.')
        analysis.append('ProgressAgent và bộ chặn loop local không chạy trong pilot này. Không thể chuyển kết luận pass ở URLKit sang runtime chính thức hoặc quy toàn bộ khác biệt cho model.')
        analysis.append('Ưu tiên tiếp: phân loại lỗi tool/đọc lặp/patch rỗng; thử prompt ví dụ arguments chính xác và hạn mức đọc trước khi sửa bằng YAML/prompt/skills được hỗ trợ. Giữ đối chứng, không tăng lượt để che loop; cần thêm issue trước khi kết luận năng lực tổng quát.')
    record['analysis']=analysis
    temporary=folder/'integration-report.json.tmp';temporary.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n');temporary.replace(folder/'integration-report.json')
    lines=['# Official-runtime integration and independent pilot','','Updated: '+record['generated_at'],'','State: '+str(state.get('status','preparing')),'',record['scope'],'',
           '## Compiler / package validation','','| Model | Valid directory | Compiled | Kaggle scored |','|---|---|---|---|']
    for model,d in validations.items():lines.append(f"| {model} | {d.get('directory_validated',False)} | {d.get('agent_compiled',False)} | False |")
    lines+=['','## Environment calibration','','| Task | Original fails | Reference passes | Usable |','|---|---|---|---|']
    for d in preflight:lines.append(f"| {d['task']} | {not d['baseline_resolved'] if 'baseline_resolved' in d else 'pending'} | {d.get('reference_resolved','pending')} | {d.get('usable','pending')} |")
    lines+=['','## Agent evaluation','','| Model | Task | Result | Seconds | Tools |','|---|---|---|---:|---:|']
    for r in rows:lines.append(f"| {r['model']} | {r['task']} | {r['status']} | {r['seconds']} | {r['tools']} |")
    lines+=['','## Phân tích sau pilot','']+['- '+item for item in analysis]
    lines+=['','## Differences from scored Kaggle runtime','']+['- '+d for d in record['differences']]
    lines+=['','Competition tasks/snapshots endpoint returned HTTP 401 without authentication. No login or competition submission performed.','',
            'Sources: [organizer wheelhouse](https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse), [organizer starter](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent), [independent dataset](https://www.kaggle.com/datasets/moshegolderson/freshswe-py).','']
    (folder/'integration-report.md').write_text('\n'.join(lines))
    def table(headers,records):
        return '<div class="scroll"><table><tr>'+''.join('<th>'+escape(x)+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in row)+'</tr>' for row in records)+'</table></div>'
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Official harness integration</title>',
          '<style>body{font:16px/1.6 system-ui;margin:30px auto;max-width:1150px;padding:0 20px;color:#182f49}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow:auto}.note{background:#edf3fa;padding:16px}</style>',
          '<h1>Harness chính thức · Pilot trên repo thật</h1><p>Cập nhật: '+escape(record['generated_at'])+'</p>',
          '<p class="note">Trạng thái: '+escape(str(state.get('status','preparing')))+' · Dùng compiler/evaluator từ wheelhouse công khai của ban tổ chức với task FreshSWE-Py độc lập. Đây chưa phải điểm Kaggle; local ProgressAgent không được sử dụng.</p>',
          '<h2>Đóng gói và compile</h2>',table(['Model','Directory valid','Compiled','Kaggle scored'],[[m,d.get('directory_validated',False),d.get('agent_compiled',False),False] for m,d in validations.items()]),
          '<h2>Kiểm chứng môi trường trước khi chạy model</h2>',table(['Task','Code gốc fail','Patch tham chiếu pass','Usable'],[[d['task'],not d['baseline_resolved'] if 'baseline_resolved' in d else 'pending',d.get('reference_resolved','pending'),d.get('usable','pending')] for d in preflight]),
          '<h2>Kết quả agent</h2>',table(['Model','Task','Result','Giây','Tools'],[[r['model'],r['task'],r['status'],r['seconds'],r['tools']] for r in rows])]
    if state.get('error'):
        html.append('<p class="note">Lỗi cần xem lại: ' + escape(str(state['error'])) + '</p>')
    for r in rows:
        if r['evidence']:html.append('<p><a href="../../'+escape(r['evidence'],quote=True)+'">'+escape(r['model']+' / '+r['task']+' · evidence')+'</a></p>')
        if r['error']:html.append('<p>'+escape(str(r['error']))+'</p>')
    html+=['<h2>Phân tích sau pilot</h2>']+['<p>'+escape(item)+'</p>' for item in analysis]
    html+=['<h2>Giới hạn so sánh</h2>']+['<p>'+escape(d)+'</p>' for d in record['differences']]
    html+=['<p>Chưa có task/snapshot chính thức vì endpoint yêu cầu xác thực; không thực hiện đăng nhập hoặc nộp bài.</p><p><a href="../study-report.html">Báo cáo local trước đó</a> · <a href="integration-report.json">JSON</a></p></html>']
    temporary=folder/'integration-report.html.tmp';temporary.write_text('\n'.join(html));temporary.replace(folder/'integration-report.html')
    return record


if __name__=='__main__':
    generate();print(ROOT/'reports/official/integration-report.html')
