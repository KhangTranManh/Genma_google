"""Per-model report only: reports/hint-ladder-v1/<model>/. No cross-model table."""
from pathlib import Path
import json,html,sys
ROOT=Path(__file__).resolve().parents[2]
ARMS=['control','A','AB','ABC']
LABEL={'control':'Đối chứng','A':'A (cơ chế)','AB':'A+B (+nguyên tắc sửa)','ABC':'A+B+C (+ví dụ cùng loại)'}


def load(p):return json.loads(p.read_text()) if p.exists() else None


def generate(model):
    run=ROOT/'runs/hint-ladder-v1'/model;out=ROOT/'reports/hint-ladder-v1'/model;out.mkdir(parents=True,exist_ok=True)
    state=load(run/'state.json') or {};pre=load(run/'preflight/summary.json');rows=[];details=''
    for arm in ARMS:
        f=run/arm;c=load(f/'classification.json');e=load(f/'execution.json')
        if c is None:continue
        api=(e or {}).get('api',{});ev=api.get('evaluation',{})
        rows.append({'arm':arm,'output_tokens':c.get('output_tokens'),'finish_reason':c.get('finish_reason'),'capture':c.get('label'),'raw_equals_api':c.get('native_equals_api'),
                     'call_valid':api.get('call_valid'),'literal_match':api.get('old_string_literal_match'),
                     'public_perf':ev.get('public_diagnostic',{}).get('passed'),'public_median_s':ev.get('public_diagnostic',{}).get('median_seconds'),
                     'functional':ev.get('functional_tests_pass'),'independent':ev.get('independent',{}).get('verified_local_fix'),
                     'long_attr':ev.get('semantic_long_attribute',{}).get('passed'),'api_accepted':api.get('accepted'),'api_category':api.get('category'),
                     'raw_category':(e or {}).get('raw',{}).get('category'),'raw_accepted':(e or {}).get('raw',{}).get('accepted')})
        details+='<details><summary>'+html.escape(LABEL[arm])+'</summary>'
        for name in ['raw-decoded.txt','parsed-calls.json','api/executed.patch','execution.json']:
            p=f/name
            if p.exists():details+='<h3>'+name+'</h3><pre>'+html.escape(p.read_text())+'</pre>'
        details+='</details>'
    (out/'comparison.json').write_text(json.dumps({'model':model,'state':state,'preflight_usable':(pre or {}).get('usable'),'rows':rows},indent=2,ensure_ascii=False)+'\n')
    keys=['arm','output_tokens','finish_reason','capture','raw_equals_api','call_valid','literal_match','public_perf','public_median_s','functional','independent','long_attr','api_accepted','api_category','raw_category']
    md=['# Hint ladder v1 — '+model.upper(),'',f"Trạng thái: `{state.get('status')}` · Preflight bộ chấm dùng được: `{(pre or {}).get('usable')}`",'',
        'Một lần sinh mỗi mức, temperature 0, trần 1536 token, mỗi mức bắt đầu từ code gốc. `api_accepted` = qua kiểm tra hiệu năng công khai, 67 test chức năng, bộ chấm độc lập và kiểm tra thuộc tính dài. Kết quả chỉ của model này; không gộp với model khác.','',
        '| '+' | '.join(keys)+' |','|'+'---|'*len(keys)]
    md+=['| '+' | '.join(LABEL[r[k]] if k=='arm' else str(r[k]) for k in keys)+' |' for r in rows]
    a=out/'analysis.md'
    (out/'comparison.md').write_text('\n'.join(md)+'\n')
    page='<!doctype html><meta charset="utf-8"><title>Hint ladder v1 '+model+'</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #aaa;padding:6px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Hint ladder v1 — '+model.upper()+'</h1><p>Trạng thái: '+html.escape(str(state.get('status')))+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(LABEL[r[k]] if k=='arm' else str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
    if a.exists():page+='<h2>Phân tích</h2><pre>'+html.escape(a.read_text())+'</pre>'
    (out/'comparison.html').write_text(page+details)

if __name__=='__main__':generate(sys.argv[1])
