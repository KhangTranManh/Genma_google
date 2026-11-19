from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    out=ROOT/'reports/stepwise-v1';out.mkdir(parents=True,exist_ok=True);rows=[]
    for model in ['12b','31b']:
        for path in sorted((ROOT/'runs/stepwise-v1'/model).glob('*/summary.json')):
            r=json.loads(path.read_text());r['model']=model;rows.append(r)
    (out/'comparison.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    page='<!doctype html><meta charset="utf-8"><title>Stepwise diagnosis</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Theo dõi từng bước: 12B và 31B</h1><p>Cùng issue w3lib_264, container riêng. Host ép chuyển bước và giới hạn tool; mỗi bước có session mới, nhận handoff của model từ bước trước (tối đa3000 ký tự/bước). Đây là chẩn đoán có điều phối, không phải điểm autonomous hoặc Kaggle. Không đưa reference patch vào prompt. Bảng ghi sự kiện, chưa tự suy diễn đúng/sai về ngữ nghĩa.</p><table><tr><th>Model</th><th>Bước</th><th>Tool calls</th><th>Giây</th><th>Diff đổi</th><th>Lỗi</th></tr>'
    for r in rows:page+='<tr>'+''.join('<td>'+html.escape(str(r.get(k)))+'</td>' for k in ['model','stage','calls','seconds','tracked_diff_changed','error'])+'</tr>'
    page+='</table>'
    for r in rows:
        folder=ROOT/'runs/stepwise-v1'/r['model']/r['stage']
        page+='<details><summary>'+r['model']+' / '+r['stage']+'</summary><h3>Input</h3><pre>'+html.escape((folder/'input.json').read_text())+'</pre><h3>Model handoff</h3><pre>'+html.escape(r['handoff'])+'</pre><h3>Tool calls và responses</h3><pre>'+html.escape(json.dumps(r['observations'],indent=2,ensure_ascii=False))+'</pre><h3>Patch sau bước này</h3><pre>'+html.escape((folder/'after.patch').read_text())+'</pre></details>'
    analysis=out/'analysis.md'
    if analysis.exists():page+='<h2>Đánh giá kết quả</h2><pre>'+html.escape(analysis.read_text())+'</pre>'
    (out/'comparison.html').write_text(page)
if __name__=='__main__':generate()
