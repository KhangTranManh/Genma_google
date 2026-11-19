from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/candidates-edit-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for p in sorted((ROOT/'runs/candidates-edit-v1').glob('*/feedback/*/execution.json')):
        f=p.parent;model=f.parts[-3];e=json.loads(p.read_text());c=json.loads((f/'classification.json').read_text());a=e['api'];g=f/'final-independent/grade.json';final=json.loads(g.read_text()) if g.exists() else {}
        row={'model':model,'attempt':f.name,'capture_label':c['label'],'generation_seconds':c.get('elapsed_seconds'),'raw_equals_api':c.get('native_equals_api'),'call_valid':a['call_valid'],'literal_match':a.get('old_string_literal_match'),'changed':a['file_changed_this_attempt'],'public_diagnostic':a['public_feedback']['diagnostic'].get('passed'),'public_tests':a['public_feedback']['functional_tests']['exit_code']==0,'public_pass':a['public_feedback']['passed'],'output_tokens':c.get('output_tokens'),'final_independent_pass':final.get('verified_local_fix','not_final_attempt')};rows.append(row)
        details+='<details><summary>'+model+' / '+f.name+'</summary>'
        for name in ['request.json','raw-decoded.txt','parsed-calls.json','execution.json','api/cumulative.patch','final-independent/grade.json']:
            path=f/name
            if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
        details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','attempt','output_tokens','capture_label','raw_equals_api','call_valid','literal_match','changed','public_diagnostic','public_tests','public_pass','final_independent_pass']
    note='C: ba candidate độc lập từ code gốc,temperature0.6 và seeds17/29/43. Chọn theo public pass, chức năng, runtime; chỉ grade độc lập candidate được chọn. Không nhận feedback từ candidate trước. Raw/API execution độc lập trong repo sạch; grader cuối không tiết lộ cho model. Một issue đã quan sát, host cung cấp block, chưa phải autonomous benchmark. None là chưa đánh giá cuối.'
    page='<!doctype html><meta charset="utf-8"><title>Feedback edit v1</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>C: candidate độc lập — 12B /31B</h1><p>'+note+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    a=out/'analysis.md'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)
if __name__=='__main__':generate()
