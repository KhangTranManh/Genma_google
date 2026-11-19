"""Brief evidence summary, no hidden reasoning requested or grader revealed."""
import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def diagnose(model,attempt,repair_instruction):
    folder=ROOT/'runs/diagnosis-edit-v1'/model/'diagnoses';folder.mkdir(parents=True,exist_ok=True)
    request={'model':f'gemma-4-{model}-it-qat-w4a16-ct','messages':[{'role':'system','content':'Write a brief repair decision summary grounded only in observed execution evidence. Return three short fields: failed_observation, suspected_cause, next_change. State uncertainty. Do not write a patch or tool call. Do not invent results.'},{'role':'user','content':repair_instruction}],'temperature':0,'max_tokens':384,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
    start=time.monotonic();req=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',data=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
    response=json.load(urllib.request.urlopen(req,timeout=180));text=response['choices'][0]['message'].get('content') or ''
    (folder/f'attempt_{attempt}.json').write_text(json.dumps({'request':request,'response':response,'elapsed_seconds':time.monotonic()-start,'decision_summary':text},indent=2,ensure_ascii=False)+'\n')
    return text
