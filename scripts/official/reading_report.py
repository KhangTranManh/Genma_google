"""Full-run and partial progress report, preserving missing data and submission origin."""
from datetime import datetime,timezone
from html import escape
import csv
import json
from pathlib import Path
import tomllib
from reading_metrics import analyze,read
ROOT=Path(__file__).resolve().parents[2]
LABELS={'baseline':'R0 · Đối chứng','prompt':'R1 · Prompt','skill':'R2 · Prompt + skill'}


def generate(root=ROOT,version="v1"):
    spec=tomllib.loads((root/('configs/reading-study-v2.toml' if version=='v2' else 'configs/reading-study.toml')).read_text())
    base=root/('runs/reading-'+version);state=read(base/'state.json');live=read(base/'live.json');rows=[];warnings=[]
    for model in spec['models']:
        for arm in spec['arm_order']:
            for task in spec['development_tasks']:
                folder=base/model/arm/task;summary=read(folder/'summary.json');inputs=read(folder/'run-inputs.json')
                metrics=analyze(folder) if summary else {}
                current=state.get('current')=={'model':model,'arm':arm,'task':task} and state.get('in_progress')
                error=summary.get('error_message') or summary.get('error') or ''
                runtime_error=any(marker.lower() in error.lower() for marker in ['ContextWindowExceeded','maximum context length','connection refused','AuthenticationError','ModelNotFound'])
                status=('runtime_error' if runtime_error else ('pass' if summary.get('resolved') else 'fail')) if summary else ('running' if current else 'pending')
                row={'model':model,'arm':arm,'task':task,'status':status,
                     'autonomous_pass':bool(summary.get('resolved') and metrics.get('explicit_nonempty_submission')) if summary else None,
                     'seconds':summary.get('duration_seconds'),'llm_calls':summary.get('total_llm_calls'),'tools':summary.get('tool_calls'),
                     'error':summary.get('error_message') or summary.get('error'), 'metrics':metrics,
                     'prompt_sha256':inputs.get('prompt_sha256'), 'base_commit':inputs.get('base_commit'),
                     'evidence':str((folder/'summary.json').relative_to(root)) if summary else None}
                rows.append(row)
                if summary and not metrics.get('trace_available'):warnings.append(f'Missing trace: {model}/{arm}/{task}')
                if summary and arm=='skill' and not metrics.get('skill_loaded_observed'):warnings.append(f'Skill load not observed: {model}/{task}; do not assume skill used.')
    assessments=[]
    for model in spec['models']:
        for task in spec['development_tasks']:
            selected={r['arm']:r for r in rows if r['model']==model and r['task']==task}
            for arm,reference in [('prompt','baseline'),('skill','prompt')]:
                a,b=selected[arm],selected[reference]
                if a['status'] in ('pending','running') or b['status'] in ('pending','running'):finding='Chờ đủ cặp.'
                elif 'runtime_error' in (a['status'],b['status']):finding='Cặp có lỗi runtime; không quy kết hiệu quả prompt/skill.'
                elif a['base_commit']!=b['base_commit']:finding='Commit không khớp; chưa so sánh.';warnings.append(model+'/'+task+': base commit mismatch')
                elif a['autonomous_pass'] and not b['autonomous_pass']:finding='Tăng tự submit + pass trên lượt này; chưa chứng minh ổn định.'
                elif b['autonomous_pass'] and not a['autonomous_pass']:finding='Regression về tự submit + pass; chưa chấp nhận candidate.'
                elif a['autonomous_pass'] and b['autonomous_pass']:finding=f"Cùng tự submit + pass; chênh lệch thời gian candidate trừ đối chứng: {a['seconds']-b['seconds']:+.1f}s."
                else:finding='Chưa cải thiện tự hoàn tất trong cặp này; xem lỗi tool, đọc lặp và patch.'
                assessments.append({'model':model,'task':task,'candidate':arm,'reference':reference,'finding':finding})
    record={'generated_at':datetime.now(timezone.utc).isoformat(),'state':state,'live':live,'rows':rows,'warnings':warnings,'assessments':assessments,
            'scope':'18 development trials on previously observed FreshSWE tasks; not holdout or Kaggle score.'}
    output=root/('reports/reading-'+version);output.mkdir(parents=True,exist_ok=True)
    tmp=output/'comparison.json.tmp';tmp.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n');tmp.replace(output/'comparison.json')
    headers=['Model','Nhánh','Issue','Kết quả','Tự submit + pass','Giây','Lượt','Read','Đọc trùng','Lỗi arguments','Skill load']
    cells=[]
    for r in rows:
        m=r['metrics'];cells.append([r['model'],LABELS[r['arm']],r['task'],r['status'],r['autonomous_pass'],r['seconds'],r['llm_calls'],m.get('read_requests'),m.get('repeated_identical_read_results'),m.get('invalid_arguments_observed'),m.get('skill_loaded_observed')])
    lines=['# Theo dõi focused reading: R0/R1/R2','',record['scope'],'','State: '+state.get('status','not_started'),'','| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    lines += ['| '+' | '.join('—' if x is None else str(x) for x in row)+' |' for row in cells]
    lines+=['','## Đánh giá theo cặp','']+[f"- {a['model']}/{a['task']}: {a['candidate']} vs {a['reference']}: {a['finding']}" for a in assessments]
    lines+=['','## Cảnh báo','']+(warnings or ['Chưa phát hiện cảnh báo về dữ liệu hoàn tất.'])
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    with (output/'comparison.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(headers);writer.writerows(cells)
    def e(x):return escape('—' if x is None else str(x))
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Focused reading · theo dõi</title><style>body{font:16px/1.6 system-ui;max-width:1350px;margin:30px auto;padding:0 20px;color:#16304b}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}th{white-space:nowrap;background:#edf3fa}.note{padding:15px;background:#edf3fa}details{padding:10px;background:#f5f7fa;margin:8px 0}</style>',
          '<h1>Đọc repo có mục tiêu · R0/R1/R2</h1><p>Cập nhật UTC: '+e(record['generated_at'])+'</p>',
          '<p class="note">State: '+e(state.get('status','not_started'))+' · Đã kết thúc '+str(sum(r['status'] in ('pass','fail','runtime_error') for r in rows))+'/18 lượt. Ba issue đã xem là development, không phải holdout hoặc điểm Kaggle.</p>',
          '<p>R0 đối chứng; R1 thêm prompt đọc có mục tiêu; R2 thêm ADK skill trên R1. 48 lượt / 96 tools / 15 phút. Giảm đọc nhưng patch sai không được coi là cải thiện. Pass test và tự submit là hai tiêu chí tách riêng.</p>']
    if state.get('error'):html.append('<p class="note">'+e(state['error'])+'</p>')
    if live:html.append('<details open><summary>Quan sát lượt hiện tại</summary><pre>'+e(json.dumps(live,indent=2,ensure_ascii=False))+'</pre></details>')
    html+=['<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr>']
    html+=['<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in cells];html+=['</table></div><h2>Đánh giá theo cặp</h2>']
    html+=['<p>'+e(a['model']+'/'+a['task']+' · '+a['candidate']+' vs '+a['reference']+': '+a['finding'])+'</p>' for a in assessments]
    for warning in warnings:html.append('<p class="note">'+e(warning)+'</p>')
    html.append('<h2>Bằng chứng từng lượt</h2>')
    for r in rows:
        if r['evidence']:
            html.append('<details><summary>'+e(r['model']+'/'+r['arm']+'/'+r['task'])+'</summary><p>'+e(r['error'])+'</p><pre>'+e(json.dumps(r['metrics'],indent=2,ensure_ascii=False))+'</pre><a href="../../'+e(r['evidence'])+'">Evaluator result</a></details>')
    html+=['<p>Đọc trùng: cùng filepath/range/content từ sau lần edit/write trực tiếp gần nhất; không đồng nghĩa mọi lượt trùng đều vô ích. Timing edit chỉ đo file tools thành công, không bao gồm sửa bằng shell. Token là tổng metrics từng agent step, không phải số billing.</p><p><a href="definition.html">Thiết kế</a> · <a href="comparison.json">JSON</a> · <a href="comparison.csv">CSV</a> · <a href="../study-report.html">Báo cáo tổng</a></p></html>']
    if version=='v2':
        html=[part.replace('href="definition.html"','href="../reading-v1/definition.html"').replace('R0/R1/R2</h1>','R0/R1/R2 · runtime v2, context 16.384</h1>') for part in html]
    tmp=output/'comparison.html.tmp';tmp.write_text('\n'.join(html));tmp.replace(output/'comparison.html')
    return record


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v1','v2'],default='v1');args=parser.parse_args()
    generate(version=args.version);print(ROOT/('reports/reading-'+args.version)/'comparison.html')
