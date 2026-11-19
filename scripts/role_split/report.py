from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/role-split-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for model in ['12b','31b']:
        base=ROOT/'runs/role-split-v1'/model
        for name in ['localize/result.json','ranking.json','selection.json']:
            p=base/name
            if p.exists():details+='<details><summary>'+model+' / '+name+'</summary><pre>'+html.escape(p.read_text())+'</pre></details>'
        for p in sorted(base.glob('role_split/*/policy.json')):
            f=p.parent;policy=json.loads(p.read_text());assignment=json.loads((f/'assignment.json').read_text());c=json.loads((f/'classification.json').read_text());e=json.loads((f/'execution.json').read_text())['api'];obs=e['observations'];review=f/'review/result.json';verdict=json.loads(review.read_text()) if review.exists() else {};final=f/'independent-final/verdict.json';g=json.loads(final.read_text()) if final.exists() else {}
            row={'model':model,'candidate':f.name,'hypothesis':assignment['hypothesis']['id'],'ochiai':assignment['ochiai_max'],'capture':c['label'],'raw_equals_api':c.get('native_equals_api'),'public_failures':obs['failure_count'],'public_pass':obs['passed'],'retain':policy['retain'],'duplicate':policy['duplicate_diff'],'review_verdict':verdict.get('verdict'),'final_independent_pass':g.get('verified_local_fix')};rows.append(row)
            details+='<details><summary>'+model+' / '+f.name+'</summary>'
            for name in ['assignment.json','request.json','raw-decoded.txt','parsed-calls.json','execution.json','policy.json','review/request.json','review/result.json','api/candidate.patch','independent-final/verdict.json']:
                path=f/name
                if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
            details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','candidate','hypothesis','ochiai','capture','raw_equals_api','public_failures','retain','duplicate','review_verdict','final_independent_pass']
    note='Cùng model, ba vai gọi riêng với messages mới: Localize không có tool; Patch chỉ nhận một giả thuyết và code gốc; Feedback chỉ nhận giả thuyết và kết quả rút gọn, không edit. Python xếp vị trí bằng coverage/Ochiai, giữ patch theo public tests và semantic guard, loại no-progress/duplicate, chọn trong patch được giữ rồi grade độc lập. K3, một candidate/giả thuyết, không dùng nhận định model để giữ/chọn. Source location được cung cấp sẵn; một issue đã quan sát. SBFL đo sự liên quan tới dòng được chạy, không chứng minh căn nguyên; không có exception stack trace cho lỗi timing này. None nghĩa chưa/không có independent grade.'
    page='<!doctype html><meta charset="utf-8"><title>Role split v1</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Một model — vai tách biệt — Python chọn</h1><p>'+note+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    a=out/'analysis.md'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)
if __name__=='__main__':generate()
