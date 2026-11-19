from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/infer-edit-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for p in sorted((ROOT/'runs/infer-edit-v1').glob('*/*/*/execution.json')):
        f=p.parent;model,arm,context=f.parts[-3:];c=json.loads((f/'classification.json').read_text());e=json.loads(p.read_text());replay=json.loads((f/'engine-replay.json').read_text());api=e.get('api',{});g=api.get('grade',{})
        r={'model':model,'arm':arm,'context':context,'input_tokens':c['prompt_tokens'],'length_validated':c.get('length_validated','short'),'raw_equals_api':c.get('native_equals_api'),'engine_matches_api':replay.get('matches_api'),'literal_match':api.get('old_string_literal_match'),'file_changed':api.get('file_changed'),'public_tests_pass':g.get('public_tests_pass'),'regression_pass':g.get('regression',{}).get('passed'),'api_category':api.get('category'),'raw_category':e.get('raw',{}).get('category')};rows.append(r)
        details+='<details><summary>'+model+' / '+arm+' / '+context+'</summary>'
        for name in ['request.json','raw-decoded.txt','parsed-calls.json','execution.json','api/executed.patch']:
            path=f/name
            if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
        details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','arm','context','input_tokens','raw_equals_api','literal_match','file_changed','public_tests_pass','regression_pass','api_category','raw_category']
    notes='12 điều kiện: hai model × có/không chỉ dẫn sửa × ngắn/4K/12K. Cùng issue đã bỏ gợi ý đáp án, cùng đoạn code và prompt làm kỹ. Một lần sinh mỗi điều kiện, native API, tool edit duy nhất, không retry. Kiểm tra riêng raw/API trên repo sạch bằng tool chính thức. verified_local_fix chỉ là kết quả bộ kiểm tra local, không phải điểm Kaggle. Grader đã xác nhận baseline thất bại và bản sửa chẩn đoán đạt trước khi chạy. Model vẫn được chỉ vị trí và block nên đây không phải autonomous repair.'
    page='<!doctype html><meta charset="utf-8"><title>Infer edit v1</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Tự suy ra cách sửa — 12B / 31B</h1><p>'+notes+'</p><p>Hoàn tất '+str(len(rows))+'/12</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    analysis=out/'analysis.md'
    if analysis.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(analysis.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)
if __name__=='__main__':generate()
