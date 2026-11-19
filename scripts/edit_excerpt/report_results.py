from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/edit-excerpt-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for model in ['12b','31b']:
        folder=ROOT/'runs/edit-excerpt-v1'/model/'excerpt/exact_excerpt'
        if not (folder/'execution.json').exists():continue
        c=json.loads((folder/'classification.json').read_text());e=json.loads((folder/'execution.json').read_text());replay=json.loads((folder/'engine-replay.json').read_text())
        row={'model':model,'raw_equals_api':c.get('native_equals_api'),'engine_matches_api':replay.get('matches_api'),'raw_execution_correct':e.get('raw',{}).get('exact_requested_result'),'api_execution_correct':e.get('api',{}).get('exact_requested_result'),'strict_arguments_label':c['label'],'prompt_tokens':c.get('prompt_tokens')};rows.append(row)
        details+='<h2>'+model+'</h2>'
        for name in ['request.json','raw-decoded.txt','parsed-calls.json','engine-replay.json','execution.json','api-executed.patch']:
            details+='<details><summary>'+name+'</summary><pre>'+html.escape((folder/name).read_text())+'</pre></details>'
    analysis='''Nhánh riêng: host cung cấp chính xác block3 dòng và yêu cầu đổi [^>]* thành [^<>]*. Mỗi model chỉ sinh một lần, chỉ được gọi edit_file. Raw call và API call được thực thi riêng bằng tool chính thức trong hai container sạch. Thành công ở đây là full file sau edit khớp chính xác thay đổi đã yêu cầu; chưa phải kiểm chứng giải issue hay benchmark hiệu năng.

Nhãn strict_arguments_label chỉ so khớp toàn bộ arguments với block kỳ vọng có newline cuối. Một replacement hợp lệ có thể không bao gồm newline đó: nếu exact_requested_result=True thì đó là edit thành công dù nhãn strict là raw_output_defect. Không dùng nhãn này để kết luận model edit sai.

So với stepwise-v1: trước đó cả hai thất bại khi old_string không khớp. Thí nghiệm này đồng thời rút ngắn context, cung cấp block chính xác, chỉ định rõ thay đổi, giới hạn còn một tool và chuyển adapter từ ADK sang native API. Vì nhiều yếu tố cùng đổi, kết quả chỉ cho thấy khả năng edit dưới điều kiện hướng dẫn cụ thể; chưa cô lập được một nguyên nhân duy nhất. Raw/API khớp trong lượt này không loại trừ parser lỗi ở lượt ADK trước.

Bước tách tiếp nên thay đổi từng yếu tố: giữ nguyên đoạn code và yêu cầu, so native API với ADK; sau đó giữ adapter và tăng context. Không gộp với điểm autonomous trước.'''
    (out/'comparison.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    keys=['model','prompt_tokens','raw_equals_api','engine_matches_api','raw_execution_correct','api_execution_correct','strict_arguments_label']
    page='<!doctype html><meta charset="utf-8"><title>Exact excerpt edit</title><style>body{font:16px system-ui;margin:30px}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px}</style><h1>Exact excerpt edit — 12B / 31B</h1><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table><pre>'+html.escape(analysis)+'</pre>'+details
    (out/'comparison.html').write_text(page);(out/'analysis.md').write_text(analysis+'\n\n'+json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':generate()
