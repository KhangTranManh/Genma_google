from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/feedback-edit-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for p in sorted((ROOT/'runs/feedback-edit-v1').glob('*/feedback/*/execution.json')):
        f=p.parent;model=f.parts[-3];e=json.loads(p.read_text());c=json.loads((f/'classification.json').read_text());a=e['api'];g=f/'final-independent/grade.json';final=json.loads(g.read_text()) if g.exists() else {}
        row={'model':model,'attempt':f.name,'capture_label':c['label'],'raw_equals_api':c.get('native_equals_api'),'call_valid':a['call_valid'],'literal_match':a.get('old_string_literal_match'),'changed':a['file_changed_this_attempt'],'public_diagnostic':a['public_feedback']['diagnostic'].get('passed'),'public_tests':a['public_feedback']['functional_tests']['exit_code']==0,'public_pass':a['public_feedback']['passed'],'final_independent_pass':final.get('verified_local_fix','not_final_attempt')};rows.append(row)
        details+='<details><summary>'+model+' / '+f.name+'</summary>'
        for name in ['request.json','raw-decoded.txt','parsed-calls.json','execution.json','api/cumulative.patch','final-independent/grade.json']:
            path=f/name
            if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
        details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','attempt','capture_label','raw_equals_api','call_valid','literal_match','changed','public_diagnostic','public_tests','public_pass','final_independent_pass']
    note='Nhánh có phản hồi riêng, context ngắn: tối đa3 generations/model (candidate đầu +2 lần sửa). Model nhận kết quả tái hiện công khai ở6000 và67 test; grader độc lập2K/4K/8K/30K cùng kiểm tra URL không tiết lộ. Mỗi candidate raw/API được thực thi riêng trên repo sạch với source tích lũy trước đó. Dừng sớm theo public check; chỉ grade độc lập candidate cuối. Host cung cấp block cập nhật và điều phối sửa lại, không phải agent tự điều hướng. So với one-shot có thêm ngân sách và handoff: chưa cô lập hiệu quả riêng của feedback.'
    page='<!doctype html><meta charset="utf-8"><title>Feedback edit v1</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Sửa lại sau phản hồi — 12B /31B</h1><p>'+note+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    a=out/'analysis.md'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)
if __name__=='__main__':generate()
