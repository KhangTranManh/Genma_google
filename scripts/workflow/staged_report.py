"""Staged workflow report; script inspections are not miscounted as zero reads."""
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path
from html import escape
import json
import sys
import tomllib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/official'))
from reading_metrics import analyze,read


def stage_metrics(folder):
    paths=sorted((folder/'traces').glob('*.json'))
    if not paths:return {'trace_available':False,'phase_llm_steps':None,'bounded_inspection_requests':None,'denied_operations':None}
    data=read(paths[0]);phases=Counter();ops=Counter();denied=Counter();sequence=[]
    for step in data.get('steps',[]):
        if step.get('source')=='agent':
            author=(step.get('extra') or {}).get('author')
            if author:
                phases[author]+=1
                if not sequence or sequence[-1]!=author:sequence.append(author)
        calls=step.get('tool_calls') or []
        try:result=json.loads((step.get('observation') or {}).get('content',''))
        except (TypeError,json.JSONDecodeError):result={}
        for call in calls:
            if call.get('function_name')!='run_skill_script':continue
            args=call.get('arguments') or {}
            if isinstance(args,str):
                try:args=json.loads(args)
                except json.JSONDecodeError:continue
            argv=args.get('args',[]) if isinstance(args,dict) else []
            action=argv[0] if isinstance(argv,list) and argv else 'unknown'
            ops[action]+=1
            if len(calls)==1 and isinstance(result,dict):
                inner=result
                if isinstance(result.get('stdout'),str):
                    try:inner=json.loads(result['stdout'])
                    except json.JSONDecodeError:inner={}
                if isinstance(inner,dict) and inner.get('status')=='denied':denied[inner.get('reason','unknown')]+=1
    return {'trace_available':True,'phase_llm_steps':dict(phases),'phase_sequence':sequence,'script_requests':dict(ops),
            'bounded_inspection_requests':ops['read']+ops['search'],'denied_operations':dict(denied),
            'note':'Requests include denials; phases are observed authors, not assumed transitions.'}


def generate(root=ROOT):
    spec=tomllib.loads((root/'configs/staged-study.toml').read_text());base=root/'runs/staged-v1';state=read(base/'state.json');live=read(base/'live.json');rows=[]
    for model in spec['models']:
        for task in spec['tasks']:
            for arm in spec['arms']:
                folder=base/model/arm/task;summary=read(folder/'summary.json')
                metrics=analyze(folder) if summary else {};stages=stage_metrics(folder) if summary else {}
                current=state.get('current')=={'model':model,'task':task,'arm':arm} and state.get('in_progress')
                error=summary.get('error_message') or summary.get('error') or ''
                runtime_error=any(m.lower() in error.lower() for m in ['ContextWindowExceeded','maximum context length','connection refused','AuthenticationError'])
                rows.append({'model':model,'task':task,'arm':arm,'status':('runtime_error' if runtime_error else ('pass' if summary.get('resolved') else 'fail')) if summary else ('running' if current else 'pending'),
                             'autonomous_pass':bool(summary.get('resolved') and metrics.get('explicit_nonempty_submission')) if summary else None,
                             'seconds':summary.get('duration_seconds'),'llm_calls':summary.get('total_llm_calls'),
                             'error':summary.get('error_message') or summary.get('error'),'metrics':metrics,'stages':stages,
                             'evidence':str((folder/'summary.json').relative_to(root)) if summary else None})
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'state':state,'live':live,'rows':rows,'scope':'Development pilot: workflow/tool-budget bundle vs fresh flat R1. Not Kaggle score.'}
    output=root/'reports/staged-v1';output.mkdir(parents=True,exist_ok=True)
    tmp=output/'comparison.json.tmp';tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');tmp.replace(output/'comparison.json')
    headers=['Model','Task','Arm','Result','Autonomous pass','Seconds','LLM calls','Native reads','Script inspections']
    values=[[r['model'],r['task'],r['arm'],r['status'],r['autonomous_pass'],r['seconds'],r['llm_calls'],r['metrics'].get('read_requests'),r['stages'].get('bounded_inspection_requests')] for r in rows]
    lines=['# Staged YAML vs flat reference','','State: '+state.get('status','preparing'),'','| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    lines+=['| '+' | '.join('—' if v is None else str(v) for v in row)+' |' for row in values]
    lines+=['','Script limits inspection execution, not LLM calls per stage. Planner has no tools; only submitter has submit_patch. Total session still shares 48 calls.','']
    (output/'comparison.md').write_text('\n'.join(lines))
    def e(v):return escape('—' if v is None else str(v))
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Staged workflow</title><style>body{font:16px/1.6 system-ui;max-width:1250px;margin:30px auto;padding:0 20px;color:#17304d}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}pre{white-space:pre-wrap}</style><h1>Workflow YAML theo giai đoạn</h1><p>State: '+e(state.get('status','preparing'))+' · '+e(state.get('waiting_for'))+'</p><p>'+e(result['scope'])+'</p><p>Planner không tool → hai vòng editor/verifier → submitter riêng. Skill giới hạn 8 inspection, 2 lần lặp cùng request, 4 lượt pytest; không ép LLM chuyển bước sau số lượt riêng. Tổng 48 lượt / 96 tools / 15 phút / context16k.</p>','<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr>']
    if live:html.insert(len(html)-1,'<details><summary>Live observation</summary><pre>'+e(json.dumps(live,indent=2,ensure_ascii=False))+'</pre></details>')
    html+=['<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in values];html+=['</table></div>']
    if state.get('error'):html.append('<p>'+e(state['error'])+'</p>')
    for r in rows:
        if r['evidence']:html.append('<details><summary>'+e(r['model']+'/'+r['arm']+'/'+r['task'])+'</summary><p>'+e(r['error'])+'</p><pre>'+e(json.dumps(r['stages'],indent=2,ensure_ascii=False))+'</pre><a href="../../'+e(r['evidence'])+'">Evaluator result</a></details>')
    if (output/'postmortem.html').exists():html.append('<p><a href="postmortem.html">Phân tích nguyên nhân thất bại và hướng tiếp theo</a></p>')
    html+=['<p><a href="../../experiments/methods/11-staged-workflow.md">Thiết kế</a> · <a href="comparison.json">JSON</a> · <a href="../study-report.html">Báo cáo tổng</a></p></html>']
    tmp=output/'comparison.html.tmp';tmp.write_text('\n'.join(html));tmp.replace(output/'comparison.html')
    return result

if __name__=='__main__':generate()
