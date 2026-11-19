"""Conservative, read-only diagnostics from official ATIF traces; no hidden tests fed back."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,json.JSONDecodeError):return {}


def source_path(path):
    parts=Path(path).parts
    name=Path(path).name
    return path.endswith('.py') and not any(p in ('tests','test','testing','.git','docs') for p in parts) and not name.startswith('test_') and not name.endswith('_test.py') and name not in ('conftest.py','setup.py')


def analyze(folder):
    folder=Path(folder)
    traces=sorted((folder/'traces').glob('*.json'))
    if not traces:
        return {'trace_available':False,'tool_requests':None,'repeated_identical_read_results':None,
                'explicit_nonempty_submission':None,'first_successful_source_file_tool_seconds':None}
    trace=read(traces[0]);counts=Counter();errors=Counter();seen=set()
    repeats=0;read_results=0;bounded=0;submit_success=0;submit_empty=0;invalid=0;suspicious=0
    first_source=None;skill_loaded=False;resources=[];prompt_tokens=[];completion_tokens=[]
    for step in trace.get('steps',[]):
        if step.get('source')=='agent':
            metrics=step.get('metrics') or {}
            if isinstance(metrics.get('prompt_tokens'),int):prompt_tokens.append(metrics['prompt_tokens'])
            if isinstance(metrics.get('completion_tokens'),int):completion_tokens.append(metrics['completion_tokens'])
        calls=step.get('tool_calls') or []
        obs=step.get('observation') or {}
        try:result=json.loads(obs.get('content',''))
        except (TypeError,json.JSONDecodeError):result=None
        for call in calls:
            name=call.get('function_name') or call.get('name')
            counts[name]+=1
            args=call.get('arguments')
            if isinstance(args,str):
                try:args=json.loads(args)
                except json.JSONDecodeError:args=None
            if not isinstance(args,dict):invalid+=1;continue
            # A single observation cannot be assigned to several calls without an id.
            response=result if len(calls)==1 and isinstance(result,dict) else None
            if response and response.get('status')=='error':
                kind=response.get('error_type','unspecified');errors[kind]+=1
                if kind in ('ValidationError','InvalidArguments','InvalidArgument','ToolArgumentError'):invalid+=1
            filepath=args.get('filepath','')
            if name=='read_file':
                if not isinstance(filepath,str) or any(marker in filepath for marker in ('start_line:', 'end_line:', '`,', '\\"start_line\\"')):
                    suspicious+=1
                if isinstance(args.get('start_line'),int) and isinstance(args.get('end_line'),int):bounded+=1
                if response and response.get('status')=='ok' and isinstance(response.get('content'),str):
                    read_results+=1
                    key=(filepath,args.get('start_line',1),args.get('end_line',150),hashlib.sha256(response['content'].encode()).hexdigest())
                    if key in seen:repeats+=1
                    seen.add(key)
            if name in ('edit_file','write_file'):
                # Conservative: reset repeat history even on a failed edit attempt.
                seen.clear()
                if first_source is None and isinstance(filepath,str) and source_path(filepath) and response and response.get('status')=='ok':
                    first_source=(call.get('extra') or step.get('extra') or {}).get('elapsed_s')
            if name=='submit_patch' and response and response.get('status')=='ok':
                if response.get('patch_size',0)>0:submit_success+=1
                else:submit_empty+=1
            if name=='load_skill' and response and not response.get('error') and response.get('status')!='error' and response.get('instructions'):
                skill_loaded=True
            if name=='load_skill_resource':resources.append({'skill_name':args.get('skill_name'),'file_path':args.get('file_path'),'observed_success':bool(response and not response.get('error') and response.get('status')!='error')})
    return {'trace_available':True,'tool_requests':dict(counts),'read_requests':counts['read_file'],
            'successful_read_results':read_results,'bounded_read_requests':bounded,
            'repeated_identical_read_results':repeats,'invalid_arguments_observed':invalid,
            'suspected_malformed_filepath_requests':suspicious,'tool_errors_by_type':dict(errors),
            'explicit_nonempty_submission':submit_success>0,'empty_submit_successes':submit_empty,
            'first_successful_source_file_tool_seconds':first_source,
            'skill_loaded_observed':skill_loaded,'skill_resource_requests':resources,
            'prompt_tokens_observed':sum(prompt_tokens) if prompt_tokens else None,
            'completion_tokens_observed':sum(completion_tokens) if completion_tokens else None,
            'token_source':'sum_agent_step_metrics; not provider-billed totals',
            'limits':'Repeated results are same filepath/range/content since the last direct edit/write attempt; not proof of wasted work. Source-edit timing excludes shell edits. Ambiguous multi-call observations are not attributed.'}
