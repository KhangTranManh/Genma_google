from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/revise-hyp-v1';out.mkdir(parents=True,exist_ok=True);rows=[];details=''
    for model in ['12b','31b']:
        base=ROOT/'runs/revise-hyp-v1'/model
        for stage in ['localize','revise']:
            missing=base/stage/'unavailable.json'
            if missing.exists():
                rows.append({'model':model,'candidate':stage+'_unavailable','hypothesis':None,'ochiai':None,'capture':'model_stage_output_unavailable','raw_equals_api':None,'public_failures':None,'public_pass':None,'retain':False,'duplicate':None,'review_hypothesis_status':None,'review_patch_status':'not_run','final_independent_pass':None})
            for artifact in ['request.json','response.json','unavailable.json']:
                path=base/stage/artifact
                if path.exists():details+='<details><summary>'+model+' / '+stage+'/'+artifact+'</summary><pre>'+html.escape(path.read_text())+'</pre></details>'
        for name in ['localize/result.json','initial-assessment.json','revise/result.json','ranking.json','selection.json']:
            p=base/name
            if p.exists():details+='<details><summary>'+model+' / '+name+'</summary><pre>'+html.escape(p.read_text())+'</pre></details>'
        ranking_path=base/'ranking.json'
        if ranking_path.exists():
            for idx,entry in enumerate(json.loads(ranking_path.read_text())['entries']):
                if entry['patch_gate']!='patch_representative':rows.append({'model':model,'candidate':'not_run_'+str(idx),'hypothesis':entry['hypothesis']['id'],'ochiai':entry['ochiai_max'],'capture':entry['patch_gate'],'raw_equals_api':None,'public_failures':None,'public_pass':None,'retain':False,'duplicate':None,'review_hypothesis_status':None,'review_patch_status':'not_run','final_independent_pass':None})
        for p in sorted(base.glob('role_split/*/policy.json')):
            f=p.parent;policy=json.loads(p.read_text());assignment=json.loads((f/'assignment.json').read_text());c=json.loads((f/'classification.json').read_text());e=json.loads((f/'execution.json').read_text())['api'];obs=e['observations'];review=f/'review/result.json';verdict=json.loads(review.read_text()) if review.exists() else ({'hypothesis_status':'unavailable','patch_status':'unavailable'} if (f/'review/unavailable.json').exists() else {});final=f/'independent-final/verdict.json';g=json.loads(final.read_text()) if final.exists() else {}
            row={'model':model,'candidate':f.name,'hypothesis':assignment['hypothesis']['id'],'ochiai':assignment['ochiai_max'],'capture':c['label'],'raw_equals_api':c.get('native_equals_api'),'public_failures':obs['failure_count'],'public_pass':obs['passed'],'retain':policy['retain'],'duplicate':policy['duplicate_diff'],'review_hypothesis_status':verdict.get('hypothesis_status'),'review_patch_status':verdict.get('patch_status'),'final_independent_pass':g.get('verified_local_fix')};rows.append(row)
            details+='<details><summary>'+model+' / '+f.name+'</summary>'
            for name in ['assignment.json','request.json','raw-decoded.txt','parsed-calls.json','execution.json','policy.json','review/request.json','review/result.json','api/candidate.patch','independent-final/verdict.json']:
                path=f/name
                if path.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(path.read_text())+'</pre>'
            details+='</details>'
    (out/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    keys=['model','candidate','hypothesis','ochiai','capture','raw_equals_api','public_failures','retain','duplicate','review_hypothesis_status','review_patch_status','final_independent_pass']
    note='Một lần sửa giả thuyết từ bốn kết quả cũ, rồi kiểm tra dự đoán trên hai probe mới chưa reveal. Model-stage unavailable không phải dự đoán sai và không được tính như patch fail. Batch complete nghĩa chạy hết ngân sách, không có nghĩa mọi model hoàn tất vai hay giải được issue. Source, issue và grader giữ riêng; chỉ một task đã biết, không phải benchmark generalization. Python chỉ cho Patch nếu prediction gate đạt; không có retained patch thì không chạy independent final grader.'
    page='<!doctype html><meta charset="utf-8"><title>Role probes v1</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Một model — sửa giả thuyết rồi probe mới — Python chọn</h1><p>'+note+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    a=out/'analysis.md'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    state_path=ROOT/'runs/revise-hyp-v1/state.json'
    status=json.loads(state_path.read_text()).get('status') if state_path.exists() else 'not_started'
    page+='<h2>Execution status</h2><p>'+html.escape(str(status))+'</p><p><a href="../role-split-v1/comparison.html">Đối chiếu role-split-v1 trước probe gate</a></p>'
    probe_rows=[]
    for model in ['12b','31b']:
        ranking=ROOT/'runs/revise-hyp-v1'/model/'ranking.json'
        if not ranking.exists():continue
        data=json.loads(ranking.read_text())
        for entry in data['entries']:
            for pred in entry['hypothesis']['predictions']:
                actual=data['original_probe_observations'][pred['probe_id']]['observed']
                probe_rows.append({'model':model,'hypothesis':entry['hypothesis']['id'],'probe':pred['probe_id'],'predicted':pred['expected'],'observed_original':actual,'gate':entry['patch_gate']})
    (out/'probe-comparison.json').write_text(json.dumps(probe_rows,indent=2)+'\n')
    columns=['model','hypothesis','probe','predicted','observed_original','gate']
    page+='<h2>Dự đoán và phép đo trên code gốc</h2><table><tr>'+''.join('<th>'+k+'</th>' for k in columns)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in columns)+'</tr>' for row in probe_rows)+'</table>'
    summary_path=out/'summary.json'
    if summary_path.exists():page+='<h2>Tổng kết model stages và ngân sách</h2><pre>'+html.escape(summary_path.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)
if __name__=='__main__':generate()
