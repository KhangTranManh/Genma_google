from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[1]
ARMS=[('baseline512','feedback-edit-v1'),('A_budget1536','feedback-budget-v1'),('B_diagnosis','diagnosis-edit-v1'),('C_independent','candidates-edit-v1')]
def generate():
    out=ROOT/'reports/repair-strategies-v1';out.mkdir(parents=True,exist_ok=True);rows=[]
    audit_path=out/'posthoc-semantic-audit.json'
    audit=json.loads(audit_path.read_text()).get('results',[]) if audit_path.exists() else []
    audit_by_key={(x['arm'],x['model']):x['posthoc_semantic_audit'].get('passed') for x in audit}
    for arm,run in ARMS:
        for model in ['12b','31b']:
            base=ROOT/'runs'/run/model;captures=list(base.glob('feedback/*/classification.json'));edits=[json.loads(p.read_text()) for p in captures];diagnoses=list((base/'diagnoses').glob('*.json'));diag=[json.loads(p.read_text()) for p in diagnoses]
            finals=list(base.glob('feedback/*/final-independent/grade.json'));g=json.loads(finals[0].read_text()) if finals else {}
            raw_requests=[json.loads((p.parent/'request.json').read_text()) for p in captures]
            actual_edits=sum(x.get('output_tokens') or 0 for x in edits);actual_diag=sum(x['response'].get('usage',{}).get('completion_tokens',0) for x in diag)
            r={'arm':arm,'model':model,'edit_generations':len(edits),'diagnosis_calls':len(diag),'output_tokens':actual_edits+actual_diag,'allowance':1536 if arm=='baseline512' else 4608,'truncated':sum(x['label']=='truncated' for x in edits),'diagnosis_truncated':sum(x['response']['choices'][0]['finish_reason']=='length' for x in diag),'posthoc_semantic_pass':audit_by_key.get((run,model)),'accepted_after_audit':(bool(g.get('verified_local_fix') and audit_by_key[(run,model)]) if (run,model) in audit_by_key else None),'final_functional_pass':g.get('public_tests_pass'),'final_regression_pass':g.get('regression',{}).get('passed'),'verified_local_fix':g.get('verified_local_fix'),'report':run+'/comparison.html','input_tokens':sum(x.get('prompt_tokens') or 0 for x in edits)+sum(x['response'].get('usage',{}).get('prompt_tokens',0) for x in diag),'generation_seconds':round(sum(x.get('elapsed_seconds') or 0 for x in edits)+sum(x.get('elapsed_seconds') or 0 for x in diag),3)};rows.append(r)
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['arm','model','edit_generations','diagnosis_calls','output_tokens','allowance','truncated','final_functional_pass','final_regression_pass','verified_local_fix','posthoc_semantic_pass','accepted_after_audit','generation_seconds']
    notes='A/B/C chạy tuần tự; baseline512 là lượt lịch sử. Cùng một issue đã biết, host cung cấp block, chưa phải đánh giá agent tự giải repo. A/B temperature0, C0.6; cùng mức trần4608 generated tokens/model nhưng actual tokens, số calls và input khác nhau. Chọn C bằng public check, grader cuối không tham gia lựa chọn. verified_local_fix là kết quả grader đóng băng, không bảo đảm đúng mọi input. posthoc_semantic_pass là kiểm tra thuộc tính dài được bổ sung sau khi thấy patch A/12B; không dùng để chọn hoặc sửa lại candidate. accepted_after_audit yêu cầu đạt cả hai. None là chưa có phép đo tương ứng. Thời gian generation gồm inference và capture/replay overhead, không phải toàn bộ walltime.'
    page='<!doctype html><meta charset="utf-8"><title>Repair strategies</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>So sánh chiến lược sửa code — 12B /31B</h1><p>'+notes+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table><p>'+ ' · '.join('<a href="../'+run+'/comparison.html">'+arm+'</a>' for arm,run in ARMS)+'</p>'
    a=out/'analysis.md'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    (out/'comparison.html').write_text(page)
if __name__=='__main__':generate()
