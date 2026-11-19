from pathlib import Path
import json,hashlib,html,tomllib
ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def main():
    out=ROOT/'reports/gate-review-v1';out.mkdir(parents=True,exist_ok=True);rows=[];provenance={}
    for run in ['role-probes-v1','revise-hyp-v1']:
        for model in ['12b','31b']:
            p=ROOT/'runs'/run/model/'ranking.json'
            if not p.exists():continue
            provenance[str(p.relative_to(ROOT))]=digest(p)
            data=json.loads(p.read_text())
            for index,entry in enumerate(data['entries']):
                h=entry['hypothesis'];record_id=f'{run}/{model}/{index}'
                rows.append({'record_id':record_id,'source_run':run,'model':model,'trajectory':run+'/'+model,'source_index':index,'hypothesis':h,'old_gate':entry['patch_gate'],'old_skipped':entry['patch_gate']!='patch_representative','old_assessment':entry['probe_assessment'],'source_ranking':str(p.relative_to(ROOT)),'source_ranking_sha256':digest(p),'historical_candidate_dir':f'runs/{run}/{model}/role_split/hypothesis_{index}' if (ROOT/'runs'/run/model/'role_split'/f'hypothesis_{index}').exists() else None,'attempt_status':'not_run','verified_patch_pass':None})
    manifest={'status':'defined_not_started','records':rows,'counts':{'hypotheses':len(rows),'skipped':sum(r['old_skipped'] for r in rows),'allowed_controls':sum(not r['old_skipped'] for r in rows)},'excluded':[{'source_run':'revise-hyp-v1','model':'12b','reason':'Localize truncated; no complete hypotheses; not three failed hypotheses'}],'source_hashes':provenance}
    assert manifest['counts']=={'hypotheses':9,'skipped':8,'allowed_controls':1}
    save(ROOT/'experiments/gate_review_v1/audit-manifest.json',manifest)
    from policies import audit_metrics
    metrics=audit_metrics(rows);save(out/'audit-status.json',dict(status='not_run',**metrics))
    parts=[('01-offline-audit.md','P0 · Audit gate','9 hồ sơ:8 từng bị skip +1 control; chạy Patch mọi hồ sơ rồi chấm độc lập.'),('02-ranking-only.md','P1 · Xếp hạng','Prediction chỉ sắp thứ tự; hard prune tắt, test quyết định giữ patch.'),('03-behavior-groups.md','P2 · Nhóm theo hành vi','Chỉ vector dự đoán giống hệt mới duplicate; không tự loại member.'),('04-proposed-probes.md','P3 · Model đề xuất probe','DSL chuỗi giới hạn, hai dự đoán đối lập commit trước chạy.'),('05-revision-budget.md','P4 · Giới hạn revise','Mặc định0, tối đa1; kiểm tra bằng probe chưa reveal, không dùng làm gate đơn lẻ.')]
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Gate review — kế hoạch từng phần</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;line-height:1.5;color:#182338}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:10px;border:1px solid #ccd3df;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f9;padding:16px}details{margin:12px 0}strong{color:#963b13}</style><h1>Đánh giá lại gate và kế hoạch5 phần</h1><p><strong>Đã định nghĩa; chưa chạy audit hoặc model mới.</strong> Chưa có bằng chứng gate dự đoán patch đúng. Chặn edit không đồng nghĩa giúp model sửa tốt hơn.</p><p>Trình tự: audit → replay thứ tự → nhóm hành vi → probe đề xuất → optional revision. Giữ tách từng yếu tố; chưa bật hard pruning.</p><table><tr><th>Phần</th><th>Thiết kế</th><th>Trạng thái</th></tr>'
    for file,title,description in parts:page+='<tr><td>'+title+'</td><td>'+description+'</td><td>Defined / not run</td></tr>'
    page+='</table><h2>Quần thể audit đã xác định</h2><p>9 hypotheses từ3 trajectory đã lưu:8 bị skip,1 được cho Patch.12B ở lượt revise không tạo hypothesis hợp lệ nên không thêm hàng giả.</p><table><tr><th>Model</th><th>Nguồn</th><th>Hypothesis</th><th>Gate cũ</th><th>Audit patch</th></tr>'
    for r in rows:page+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['model'],r['source_run'],r['hypothesis']['id'],r['old_gate'],'Chưa chạy'])+'</tr>'
    page+='</table><h2>Cách đọc kết quả</h2><p>Đo cả patch pass bị skip / skipped được chấm và patch pass bị skip / tổng patch pass. Nếu không có patch pass, tỷ lệ loại nhầm trong nhóm thành công là <strong>chưa xác định</strong>, không phải0%. Generation failure và infrastructure missing được ghi riêng. Kết quả1 issue không chứng minh gate an toàn trên task khác.</p><h2>Điều chỉnh kết luận cũ</h2><p>Chưa quan sát Patch cho8 hồ sơ bị skip; chưa thể nói gate đã loại được các hướng không thể sửa. Các policy cũ chỉ chứng minh được việc thi hành điều kiện, không chứng minh điều kiện có ích. Ngoài ra, rule “không có dự đoán trái nhau” trước đây rộng hơn duplicate vector và có thể gom nhầm các dự đoán khác nhau.</p>'
    for file,title,_ in parts:page+='<details><summary>'+title+' · đặc tả đầy đủ</summary><pre>'+html.escape((ROOT/'experiments/gate_review_v1'/file).read_text())+'</pre></details>'
    page+='<h2>Hiện đã có gì?</h2><p>Đặc tả5 phần, cấu hình riêng, manifest có source hashes, helper ranking/grouping/DSL validator và metric denominator. Chưa có audit inference runner, patch outcomes mới, sandbox adapter cho probe đề xuất hoặc bằng chứng cải thiện. Không cài service/timer mới.</p><p><a href="../study-report.html">Báo cáo tổng</a> · <a href="../../experiments/gate_review_v1/audit-manifest.json">Audit manifest</a></p></html>'
    (out/'plan.html').write_text(page)
    md=['# Gate review v1 — defined, not started','', 'Prior gate utility is unmeasured. Offline audit is priority zero.','', '| Part | Plan | State |','|---|---|---|']+[f'| {title} | {desc} | Defined/not run |' for _,title,desc in parts]+['', 'Audit population:9 records,8 skipped,1 allowed control. Exclude truncated12B Localize. New patch outcomes: none. False-negative rate: undefined/not measured.','', 'Configurations: configs/gate-review/*.toml. Full definitions: experiments/gate_review_v1/01..05 markdown files. HTML: reports/gate-review-v1/plan.html. No GPU job or timer started.']
    (out/'summary.md').write_text('\n'.join(md)+'\n')
    files=list((ROOT/'experiments/gate_review_v1').glob('*'))+list((ROOT/'configs/gate-review').glob('*.toml'))+list((ROOT/'scripts/gate_review').glob('*.py'))
    save(out/'definition.json',{'status':'defined_not_started','counts':manifest['counts'],'source_artifact_hashes':provenance,'definition_file_hashes':{str(p.relative_to(ROOT)):digest(p) for p in files if p.is_file()},'new_generations':0,'gpu_jobs_started':False})
    for p in (ROOT/'configs/gate-review').glob('*.toml'):tomllib.loads(p.read_text())
    print('Defined5 parts; audit manifest9 hypotheses /8 skipped /1 allowed; no inference launched.')
if __name__=='__main__':main()
