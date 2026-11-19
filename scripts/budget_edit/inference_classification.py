from native_nested import decode,equal

def valid(calls):
    if len(calls)!=1 or calls[0].get('name')!='edit_file':return False
    a=calls[0].get('arguments',{})
    return isinstance(a,dict) and a.get('filepath')=='w3lib/html.py' and all(isinstance(a.get(k),str) for k in ['old_string','new_string']) and bool(a['old_string']) and set(a)<=set(['filepath','old_string','new_string','allow_multiple']) and ('allow_multiple' not in a or isinstance(a['allow_multiple'],bool))
def classify(case,raw,api,finish_reason,has_token_ids=True):
    if finish_reason=='length':return {'label':'truncated'}
    if not has_token_ids or raw is None:return {'label':'missing_raw_capture'}
    try:calls=decode(raw)
    except ValueError as e:return {'label':'unsupported_capture','reason':str(e),'api_call_valid':valid(api)}
    same=equal(calls,api)
    return {'label':'captured' if same else 'parser_difference','native_equals_api':same,'native_call_valid':valid(calls),'api_call_valid':valid(api),'independent_native_calls':calls}
