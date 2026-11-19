"""Capture one native API generation and replay the installed parser, never execute tools."""
from datetime import datetime,timezone
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from gemma_lab.config import load
sys.path.insert(0,str(ROOT/'scripts/probes_stress'))
from inference_classification import classify
from calibration import extend


def dump(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def normalize(calls):
    result=[]
    for call in calls or []:
        fn=call.get('function',call)
        args=fn.get('arguments',{})
        if isinstance(args,str):
            try:args=json.loads(args)
            except json.JSONDecodeError:args={'__invalid_json__':args}
        result.append({'name':fn.get('name'),'arguments':args})
    return result


def run(model,arm,case_id):
    cases=json.loads((ROOT/'experiments/infer_edit_v1/cases.json').read_text())[arm];case=next(c for c in cases if c['id']==case_id)
    folder=ROOT/'runs/infer-edit-v1'/model/arm/case_id
    if folder.exists():raise FileExistsError('Preserve previous captures: '+str(folder))
    tools=json.loads((ROOT/'experiments/infer_edit_v1/tools.json').read_text())
    project=load(ROOT/'configs/project.toml');selected=project.raw['models'][model];alias=selected['alias']
    served=json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/models',timeout=5))
    if not any(m['id']==alias and m.get('max_model_len')==16384 for m in served['data']):raise RuntimeError('Wrong model is served')
    request={'model':alias,'messages':[{'role':'system','content':'Repair the reported repository defect using the supplied source evidence. Emit one edit_file call. The driver executes and grades the call independently. Do not invent a tool response or answer in prose.'},{'role':'user','content':case['instruction']}],
             'tools':tools,'tool_choice':'auto','temperature':0,'max_tokens':512,'stream':False,
             'return_token_ids':True,'return_prompt_text':True,'skip_special_tokens':False,'include_reasoning':True,
             'chat_template_kwargs':{'enable_thinking':False}}
    calibration=None
    if case['target_prompt_tokens']:
        from vllm.tokenizers import get_tokenizer
        length_tokenizer=get_tokenizer(ROOT/selected['path'],local_files_only=True,trust_remote_code=False)
        request,calibration=extend(request,length_tokenizer,target=case['target_prompt_tokens'])
    folder.mkdir(parents=True);dump(folder/'request.json',request)
    dump(folder/'case.json',case)
    if calibration:dump(folder/'length-calibration.json',calibration)
    started=time.monotonic()
    try:
        req=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions',data=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
        response=json.load(urllib.request.urlopen(req,timeout=120));dump(folder/'response.json',response)
        choice=response['choices'][0];ids=choice.get('token_ids');api=normalize(choice['message'].get('tool_calls'))
        dump(folder/'parsed-calls.json',api);dump(folder/'output-token-ids.json',ids)
        raw=None;replay={}
        tokenizer_files={}
        if ids:
            from vllm.tokenizers import get_tokenizer
            tokenizer_path=ROOT/selected['path']
            tokenizer=get_tokenizer(tokenizer_path,local_files_only=True,trust_remote_code=False)
            raw=tokenizer.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
            (folder/'raw-decoded.txt').write_text(raw)
            for name in ['tokenizer.json','tokenizer_config.json','special_tokens_map.json']:
                p=tokenizer_path/name
                if p.exists():tokenizer_files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
            try:
                from vllm.parser.gemma4 import Gemma4Parser
                from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
                parsed_request=ChatCompletionRequest(**request)
                engine=Gemma4Parser(tokenizer,tools=parsed_request.tools)
                if response.get('prompt_token_ids'):engine.set_prompt_token_ids(response['prompt_token_ids'])
                reasoning,content,calls=engine.parse(raw,parsed_request,enable_auto_tools=True,model_output_token_ids=ids)
                replay_calls=normalize([{'name':c.name,'arguments':c.arguments} for c in calls or []])
                replay={'calls':replay_calls,'matches_api':replay_calls==api,'reasoning':reasoning,'content':content}
            except Exception as error:replay={'error':type(error).__name__+': '+str(error)}
        else:(folder/'raw-decoded.txt').write_text('')
        dump(folder/'engine-replay.json',replay)
        result=classify(case,raw,api,choice.get('finish_reason'),bool(ids))
        result.update(model=model,arm=arm,case=case_id,pair_reference=case.get('pair_reference','infer_edit_v1'),prompt_tokens=response.get('usage',{}).get('prompt_tokens'),elapsed_seconds=round(time.monotonic()-started,3),output_tokens=len(ids) if ids else None,tools_executed=0)
        if case['target_prompt_tokens']:
            actual=response.get('usage',{}).get('prompt_tokens')
            result['length_validated']=isinstance(actual,int) and abs(actual-case['target_prompt_tokens'])<=128
        dump(folder/'classification.json',result)
        runtime={'time':datetime.now(timezone.utc).isoformat(),'served_models':served,'checkpoint_revision':selected.get('revision'),
                 'versions':{x:importlib.metadata.version(x) for x in ['vllm','transformers','torch']},'tokenizer_files_sha256':tokenizer_files,
                 'arm':arm,'schema_sha256':hashlib.sha256((ROOT/'experiments/infer_edit_v1/tools.json').read_bytes()).hexdigest(),'same_generation_ids':bool(ids),'api_response_id':response.get('id'),'execute_tools':False}
        dump(folder/'runtime.json',runtime)
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return result
    except Exception as error:
        dump(folder/'error.json',{'type':type(error).__name__,'message':str(error)});raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['12b','31b'],required=True);parser.add_argument('--arm',choices=['explicit_fix','infer_fix'],required=True);parser.add_argument('--case',required=True)
    args=parser.parse_args();run(args.model,args.arm,args.case)
