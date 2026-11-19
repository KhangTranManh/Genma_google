"""Report same-generation raw/parsed captures; no tools or model calls."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from html import escape
import json
ROOT=Path(__file__).resolve().parents[2]


def read(path):
    try:return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError):return {}


def generate(root=ROOT):
    base=root/'runs/toolcall-probe-v1';cases=json.loads((root/'experiments/toolcall_probe_v1/cases.json').read_text());rows=[]
    for model in ['12b','31b']:
        for case in cases:
            folder=base/model/case['id'];d=read(folder/'classification.json');replay=read(folder/'engine-replay.json')
            rows.append({'model':model,'case':case['id'],'label':d.get('label','pending'),
                         'native_expected_match':d.get('native_expected_match'),'api_expected_match':d.get('api_expected_match'),
                         'native_equals_api':d.get('native_equals_api'),'replay_matches_api':replay.get('matches_api'),
                         'output_tokens':d.get('output_tokens'),'elapsed_seconds':d.get('elapsed_seconds'),
                         'reason':d.get('reason'),'error':read(folder/'error.json') or replay.get('error'),
                         'evidence':str(folder.relative_to(root)) if d else None})
    labels=Counter(r['label'] for r in rows if r['label']!='pending')
    record={'generated_at':datetime.now(timezone.utc).isoformat(),'state':read(base/'state.json'),'rows':rows,'label_counts':dict(labels),
            'inference_requests_captured':sum(labels.values()),'tools_executed':0,
            'limits':'Eight short single-call requests; not long conversations, streaming, real-repo solving or an error-rate estimate.'}
    output=root/'reports/toolcall-probe-v1';output.mkdir(parents=True,exist_ok=True)
    (output/'comparison.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    lines=['# Same-generation tool-call/parser probe','',record['limits'],'',f"Captured {record['inference_requests_captured']}/8. Tools executed: 0.",'',
           '| Model | Case | Label | Raw expected | API expected | Replay = API |','|---|---|---|---|---|---|']
    for r in rows:lines.append(f"| {r['model']} | {r['case']} | {r['label']} | {r['native_expected_match']} | {r['api_expected_match']} | {r['replay_matches_api']} |")
    interpretation=[]
    completed=[r for r in rows if r['label']!='pending']
    matched=sum(r['native_equals_api'] is True and r['replay_matches_api'] is True for r in completed)
    interpretation.append(f'{matched}/{len(completed)} capture có native arguments, API arguments và engine replay khớp nhau. Chưa tái hiện mất/ghép field do parser trong bộ ca nhỏ này.')
    if any(r['model']=='12b' and r['case']=='edit_exact_line' and r['label']=='raw_output_defect' for r in rows):
        interpretation.append('12B/edit_exact_line: output gốc là read_file(src/example.py), trong khi yêu cầu edit_file. Đây là lệch lựa chọn tool so với yêu cầu, không phải native syntax hỏng hay field bị parser làm mất. Có thể liên quan thói quen đọc trước sửa; phép thử chưa xác định cơ chế nội tại.')
    interpretation.append('Chưa kiểm tra ADK/LiteLLM response adapter, streaming, chuỗi hội thoại dài hoặc run_skill_script với arguments lồng nhau. Không kết luận parser hoàn toàn không lỗi hoặc quy mọi thất bại repo cho model.')
    interpretation.append('Bước tiếp theo nên tái hiện một trường hợp từng lỗi bằng context/schema phức tạp hơn, vẫn thu raw và parsed cùng generation; không sửa parser hoặc weights chỉ dựa vào 8 mẫu này.')
    record['interpretation']=interpretation
    (output/'comparison.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    lines+=['','## Diễn giải','']+['- '+v for v in interpretation]
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    def e(v):return escape('—' if v is None else str(v))
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raw vs parsed tool calls</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:30px auto;padding:0 20px;color:#17304d}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;background:#f4f6fa;padding:15px}details{margin:10px 0}</style><h1>Raw token → parser → arguments</h1><p>Cập nhật UTC: '+e(record['generated_at'])+' · Đã capture '+str(record['inference_requests_captured'])+'/8 · Không thực thi tool.</p><p>Raw và arguments lấy từ cùng response; replay bằng Gemma4Parser của vLLM cục bộ. Nhãn parser mismatch chỉ là nghi vấn cần kiểm chứng. Decoder độc lập chỉ hỗ trợ native syntax phẳng trong bốn case này.</p>',
          '<div class="scroll"><table><tr>'+''.join('<th>'+x+'</th>' for x in ['Model','Case','Label','Raw đúng','API đúng','Replay = API'])+'</tr>']
    html+=['<tr>'+''.join('<td>'+e(v)+'</td>' for v in [r['model'],r['case'],r['label'],r['native_expected_match'],r['api_expected_match'],r['replay_matches_api']])+'</tr>' for r in rows]
    html+=['</table></div><p>Tám request ngắn chưa đủ loại trừ lỗi ở context dài, streaming, tool schema phức tạp hoặc adapter ADK. Không dùng tỷ lệ này làm điểm sửa repo.</p>']
    if record['state'].get('error'):html.append('<p>'+e(record['state']['error'])+'</p>')
    html.append('<h2>Diễn giải kết quả</h2>')
    html+=['<p>'+e(v)+'</p>' for v in interpretation]
    for r in rows:
        if r['evidence']:
            folder=root/r['evidence'];raw=(folder/'raw-decoded.txt').read_text() if (folder/'raw-decoded.txt').exists() else ''
            html.append('<details><summary>'+e(r['model']+' / '+r['case']+' / '+r['label'])+'</summary><p>Native raw:</p><pre>'+e(raw)+'</pre><p>API parsed:</p><pre>'+e(json.dumps(read(folder/'parsed-calls.json'),indent=2,ensure_ascii=False))+'</pre><p><a href="../../'+e(r['evidence'])+'/response.json">Response gốc</a> · <a href="../../'+e(r['evidence'])+'/engine-replay.json">Engine replay</a></p></details>')
    html.append('<p><a href="../../experiments/methods/13-toolcall-parser-probe.md">Định nghĩa</a> · <a href="comparison.json">JSON</a> · <a href="../study-report.html">Báo cáo tổng</a></p></html>')
    (output/'comparison.html').write_text('\n'.join(html))
    return record

if __name__=='__main__':generate()
