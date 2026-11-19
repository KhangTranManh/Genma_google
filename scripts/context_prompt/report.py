from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/context-prompt-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for p in sorted((ROOT/'runs/context-prompt-v1').glob('*/*/*/execution.json')):
        folder=p.parent;model,arm,case=folder.parts[-3:];c=json.loads((folder/'classification.json').read_text());e=json.loads(p.read_text());replay=json.loads((folder/'engine-replay.json').read_text())
        r={'model':model,'prompt':arm,'context':case,'input_tokens':c['prompt_tokens'],'raw_equals_api':c.get('native_equals_api'),'engine_matches_api':replay.get('matches_api'),'raw_edit_correct':e.get('raw',{}).get('exact_requested_result',False),'api_edit_correct':e.get('api',{}).get('exact_requested_result',False),'length_validated':c.get('length_validated','short'),'seconds':c['elapsed_seconds']};rows.append(r)
        details+='<details><summary>'+model+' / '+arm+' / '+case+'</summary>'
        for name in ['raw-decoded.txt','parsed-calls.json','execution.json','api-executed.patch']:
            path=folder/name
            if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
        details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','prompt','context','input_tokens','raw_equals_api','raw_edit_correct','api_edit_correct','length_validated','seconds']
    notes='So sánh 2 model × 2 prompt × 3 mức context =12 lần sinh. Context bổ sung là code thật từ repo, đóng vai trò dữ liệu tham khảo, không phải lịch sử agent nhiều lượt. Host vẫn cung cấp block và phép sửa chính xác ở cuối input. Cửa sổ server16384, output512, temperature0, thinking off, native API và schema giữ nguyên. Một lần/cell không ước lượng độ ổn định. Đúng = file sau thực thi tool khớp chính xác thay đổi yêu cầu; không phải điểm giải issue hay benchmark hiệu năng. Nhãn strict_arguments không quyết định thành công vì replacement không chứa newline cuối vẫn có thể hợp lệ. So theo hàng cùng model/context để xem tác động prompt; cùng model/prompt để xem context.'
    page='<!doctype html><meta charset="utf-8"><title>Context × prompt</title><style>body{font:16px system-ui;margin:30px}td,th{padding:8px;border:1px solid #aaa}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Context × prompt — 12B / 31B</h1><p>'+notes+'</p><p>Hoàn thành '+str(len(rows))+'/12</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'+details
    analysis=out/'analysis.md'
    if analysis.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(analysis.read_text())+'</pre>'
    (out/'comparison.html').write_text(page)
if __name__=='__main__':generate()
