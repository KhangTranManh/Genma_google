"""Separate synthetic tool diagnostics from real-issue outcomes."""
from datetime import datetime,timezone
from pathlib import Path
from html import escape
import json
import sys
import tomllib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from reading_metrics import analyze,read


def generate(root=ROOT):
    plan=tomllib.loads((root/'configs/simple-study.toml').read_text());base=root/'runs/simple-v1';state=read(base/'state.json');live=read(base/'live.json')
    micros=[];rows=[]
    for model in plan['models']:
        for case in plan['micro_cases']:
            path=base/'micro'/model/case/'summary.json';d=read(path)
            micros.append({'model':model,'case':case,'status':('pass' if d.get('diagnostic_pass') else 'fail') if d else 'pending',
                           'independent_pass':d.get('independent_pass'),'explicit_submit':d.get('explicit_submit'),
                           'required_tools_exercised':d.get('required_tools_exercised'),'tool_errors':d.get('tool_errors'),
                           'seconds':d.get('seconds'),'error':d.get('error'),'evidence':str(path.relative_to(root)) if d else None})
        for task in plan['tasks']:
            for arm in plan['arms']:
                folder=base/'real'/model/arm/task;d=read(folder/'summary.json');metrics=analyze(folder) if d else {}
                current=state.get('current')=={'phase':'real','model':model,'task':task,'arm':arm} and state.get('in_progress')
                error=d.get('error_message') or d.get('error') or ''
                runtime_error=any(s.lower() in error.lower() for s in ['ContextWindowExceeded','maximum context length','connection refused','AuthenticationError'])
                rows.append({'model':model,'task':task,'arm':arm,'status':('runtime_error' if runtime_error else ('pass' if d.get('resolved') else 'fail')) if d else ('running' if current else 'pending'),
                             'autonomous_pass':bool(d.get('resolved') and metrics.get('explicit_nonempty_submission')) if d else None,
                             'seconds':d.get('duration_seconds'),'turns':d.get('total_llm_calls'),'error':error or None,
                             'metrics':metrics,'evidence':str((folder/'summary.json').relative_to(root)) if d else None})
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'state':state,'live':live,'micro':micros,'real':rows,
            'scope':'Tool diagnostics are synthetic; real tasks are development data, not holdout or Kaggle score.'}
    output=root/'reports/simple-v1';output.mkdir(parents=True,exist_ok=True)
    tmp=output/'comparison.json.tmp';tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');tmp.replace(output/'comparison.json')
    def e(x):return escape('—' if x is None else str(x))
    def table(headers,cells):return '<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in cells)+'</table></div>'
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Simple direct tools</title><style>body{font:16px/1.6 system-ui;max-width:1250px;margin:30px auto;padding:0 20px;color:#18314d}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap}</style><h1>Một agent · tool trực tiếp · prompt ngắn</h1><p>State: '+e(state.get('status','preparing'))+' · '+e(state.get('current'))+'</p><p>Không skill, không subagent, không hard-cap riêng cho đọc. Giữ giới hạn phiên chung. Bài nhỏ kiểm tra API tool, không được gộp vào tỷ lệ giải issue thật.</p>',
          '<h2>Chẩn đoán tool trên file nhỏ — 4 lượt</h2>',table(['Model','Case','Result','Clean grader','Submit','Đủ tools yêu cầu','Lỗi tool','Giây'],[[r['model'],r['case'],r['status'],r['independent_pass'],r['explicit_submit'],r['required_tools_exercised'],r['tool_errors'],r['seconds']] for r in micros]),
          '<h2>Repo thật — 12 lượt đối chứng mới</h2>',table(['Model','Task','Arm','Result','Tự submit + pass','Giây','Lượt','Reads','Đọc trùng'],[[r['model'],r['task'],r['arm'],r['status'],r['autonomous_pass'],r['seconds'],r['turns'],r['metrics'].get('read_requests'),r['metrics'].get('repeated_identical_read_results')] for r in rows])]
    if live:html.append('<details><summary>Live observation</summary><pre>'+e(json.dumps(live,indent=2,ensure_ascii=False))+'</pre></details>')
    if state.get('error'):html.append('<p>'+e(state['error'])+'</p>')
    for r in micros+rows:
        if r['evidence']:html.append('<p><a href="../../'+e(r['evidence'])+'">'+e(r['model']+' / '+r.get('case',r.get('task',''))+' / '+r.get('arm','micro'))+'</a> · '+e(r.get('error'))+'</p>')
    html.append('<p>Control là bản flat R1 dài hơn, cùng model/tool/schema/runtime. Một lượt mỗi cell chưa đủ kết luận ổn định. Trace là output đã parse, chưa xác định lỗi weights hay parser. Tool errors gồm cả lệnh test trả thất bại, không mặc định là lỗi schema.</p><p><a href="../../experiments/methods/12-simple-direct.md">Thiết kế</a> · <a href="comparison.json">JSON</a> · <a href="../study-report.html">Báo cáo tổng</a></p></html>')
    tmp=output/'comparison.html.tmp';tmp.write_text('\n'.join(html));tmp.replace(output/'comparison.html')
    return result

if __name__=='__main__':generate()
