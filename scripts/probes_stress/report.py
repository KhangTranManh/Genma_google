from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def generate():
    base=ROOT/'runs/toolcall-stress-v1';out=ROOT/'reports/toolcall-stress-v1';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for p in sorted(base.glob('*/*/*/classification.json')):
        r=json.loads(p.read_text());replay=json.loads((p.parent/'engine-replay.json').read_text());r['engine_matches_api']=replay.get('matches_api');rows.append(r)
    (out/'comparison.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    lines=['# Tool-call stress v1','', 'Three separate arms; 24 planned captures, no tool execution. Long context is synthetic background, not multi-turn history. Skill uses a different interface and task mix; do not compare aggregate rates as a pure nesting effect. Single observations, no statistical claims.','', '| Model | Arm | Case | Input tokens | Classification | Engine = API | Length valid |','|---|---|---|---:|---|---|---|']
    for r in rows:lines.append('| '+' | '.join(str(r.get(k,'—')) for k in ['model','arm','case','prompt_tokens','label','engine_matches_api','length_validated'])+' |')
    analysis=(out/'analysis.md').read_text() if (out/'analysis.md').exists() else ''
    lines.extend(['',analysis])
    (out/'comparison.md').write_text('\n'.join(lines)+'\n')
    headers=['model','arm','case','prompt_tokens','label','engine_matches_api','length_validated']
    table='<table><tr>'+''.join('<th>'+k+'</th>' for k in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,'—')))+'</td>' for k in headers)+'</tr>' for r in rows)+'</table>'
    (out/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Tool-call stress v1</title><style>body{font:16px system-ui;margin:32px}table{border-collapse:collapse}td,th{padding:9px;border:1px solid #ccc}</style><h1>Tool-call stress v1</h1><p>'+html.escape(lines[2])+'</p><p>Completed: '+str(len(rows))+'/24</p>'+table+'<h2>Phân tích</h2><pre style="white-space:pre-wrap">'+html.escape(analysis)+'</pre>'+''.join('<details><summary>'+html.escape(r['model']+' / '+r['arm']+' / '+r['case'])+'</summary><p>Raw output</p><pre style="white-space:pre-wrap">'+html.escape((base/r['model']/r['arm']/r['case']/'raw-decoded.txt').read_text())+'</pre><p>API parsed calls</p><pre style="white-space:pre-wrap">'+html.escape((base/r['model']/r['arm']/r['case']/'parsed-calls.json').read_text())+'</pre></details>' for r in rows))
if __name__=='__main__':generate()
