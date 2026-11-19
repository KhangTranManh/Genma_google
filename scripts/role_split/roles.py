from pathlib import Path
import json,time,urllib.request
ROOT=Path(__file__).resolve().parents[2]
HYP_SCHEMA={'type':'object','properties':{'hypotheses':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'object','properties':{'id':{'type':'string'},'filepath':{'type':'string'},'start_line':{'type':'integer'},'end_line':{'type':'integer'},'cause':{'type':'string'},'predicted_failure':{'type':'string'}},'required':['id','filepath','start_line','end_line','cause','predicted_failure'],'additionalProperties':False}}},'required':['hypotheses'],'additionalProperties':False}
VERDICT_SCHEMA={'type':'object','properties':{'verdict':{'type':'string','enum':['supported','rejected','uncertain']},'evidence_summary':{'type':'string'},'remaining_uncertainty':{'type':'string'}},'required':['verdict','evidence_summary','remaining_uncertainty'],'additionalProperties':False}

def call(model,role,prompt,folder,schema,max_tokens):
    folder.mkdir(parents=True,exist_ok=False)
    system={'localize':'List exactly three distinct causal hypotheses with source locations and observable failure predictions. Do not edit, produce a patch, or rank your own proposals. Base statements on the supplied evidence.','feedback':'Assess only the assigned hypothesis against the compact observed results. Return supported, rejected or uncertain with brief evidence and remaining uncertainty. Do not write a patch, propose edits, or select the winning patch.'}[role]
    request={'model':f'gemma-4-{model}-it-qat-w4a16-ct','messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0,'max_tokens':max_tokens,'stream':False,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_schema','json_schema':{'name':role,'strict':True,'schema':schema}}}
    (folder/'request.json').write_text(json.dumps(request,indent=2)+'\n');start=time.monotonic();req=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',data=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
    response=json.load(urllib.request.urlopen(req,timeout=240));(folder/'response.json').write_text(json.dumps(response,indent=2)+'\n')
    if response['choices'][0]['finish_reason']=='length':raise RuntimeError(role+' truncated; keep artifacts for review')
    value=json.loads(response['choices'][0]['message']['content']);(folder/'result.json').write_text(json.dumps(value,indent=2)+'\n');(folder/'timing.json').write_text(json.dumps({'seconds':time.monotonic()-start})+'\n');return value
