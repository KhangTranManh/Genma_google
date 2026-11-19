from pathlib import Path
import json,html
from policies import audit_metrics
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/gate-review-v1';out.mkdir(parents=True,exist_ok=True);manifest=json.loads((ROOT/'experiments/gate_review_v1/audit-manifest.json').read_text());rows=[];details=''
    for record in manifest['records']:
        case=record['record_id'].replace('/','__');folder=ROOT/'runs/gate-audit-v1'/record['model']/'audit'/case;path=folder/'outcome.json';result=json.loads(path.read_text()) if path.exists() else {'attempt_status':'not_run','verified_patch_pass':None};row=dict(record,**result);rows.append(row)
        if path.exists():
            details+='<details><summary>'+html.escape(record['record_id'])+'</summary>'
            for name in ['request.json','raw-decoded.txt','parsed-calls.json','outcome.json','candidate.patch']:
                p=folder/name
                if p.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(p.read_text())+'</pre>'
            details+='</details>'
    metrics=audit_metrics(rows);save={'status':'complete' if metrics['scorable']==9 else 'incomplete','metrics':metrics,'by_model':{m:audit_metrics([r for r in rows if r['model']==m]) for m in ['12b','31b']},'records':rows}
    (out/'audit-results.json').write_text(json.dumps(save,indent=2)+'\n')
    page='<!doctype html><meta charset="utf-8"><title>Counterfactual gate audit</title><style>body{font:16px system-ui;margin:30px}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #aaa}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Audit: Patch cho hypotheses từng bị skip</h1><p>9 hồ sơ gốc, không deduplicate trước Patch. Một generation/model-hypothesis, cùng prompt template. Kiểm tra API patch bằng public và independent tests; labels evaluator không dùng để sửa/chọn lại candidate.</p><pre>'+html.escape(json.dumps(metrics,indent=2))+'</pre><p>FNR=null khi không có patch pass; không chứng minh gate an toàn. Mẫu chỉ1 issue và hypotheses phụ thuộc nhau.</p><table><tr><th>Model / hồ sơ</th><th>Old skip</th><th>Attempt</th><th>Patch verified pass</th><th>Reason</th></tr>'
    for r in rows:page+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['record_id'],r['old_skipped'],r['attempt_status'],r['verified_patch_pass'],r.get('reason')])+'</tr>'
    analysis=out/'audit-analysis.md'
    if analysis.exists():page+='</table><h2>Phân tích</h2><pre>'+html.escape(analysis.read_text())+'</pre>'
    else:page+='</table>'
    page+='<p><a href="plan.html">Kế hoạch5 phần</a></p>'+details;(out/'audit.html').write_text(page)
if __name__=='__main__':generate()
