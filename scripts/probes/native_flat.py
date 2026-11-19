"""Independent strict decoder for the flat native calls in this probe, not a universal parser."""
import re
DELIM='<|"|>'


def decode(raw):
    calls=[];position=0
    while True:
        match=re.search(r'<\|tool_call>call:([A-Za-z_]\w*)\{',raw[position:])
        if not match:break
        index=position+match.end();args={}
        while True:
            while index<len(raw) and raw[index].isspace():index+=1
            if index>=len(raw):raise ValueError('Incomplete call')
            if raw[index]=='}':index+=1;break
            key=re.match(r'([A-Za-z_]\w*)\s*:',raw[index:])
            if not key:raise ValueError('Unsupported key syntax')
            name=key[1];index+=key.end()
            while index<len(raw) and raw[index].isspace():index+=1
            if raw.startswith(DELIM,index):
                index+=len(DELIM);end=raw.find(DELIM,index)
                if end<0:raise ValueError('Unclosed string delimiter')
                value=raw[index:end];index=end+len(DELIM)
            else:
                end=index
                while end<len(raw) and raw[end] not in ',}':end+=1
                word=raw[index:end].strip()
                if re.fullmatch(r'-?\d+',word):value=int(word)
                elif word in ('true','false'):value=word=='true'
                elif word=='null':value=None
                else:raise ValueError('Unsupported non-string value')
                index=end
            if name in args:raise ValueError('Duplicate key')
            args[name]=value
            while index<len(raw) and raw[index].isspace():index+=1
            if index<len(raw) and raw[index]==',':index+=1;continue
            if index<len(raw) and raw[index]=='}':continue
            raise ValueError('Missing field separator')
        while index<len(raw) and raw[index].isspace():index+=1
        if not raw.startswith('<tool_call|>',index):raise ValueError('Missing closing tool-call token')
        calls.append({'name':match[1],'arguments':args});position=index+len('<tool_call|>')
    if not calls:raise ValueError('No supported complete flat native call')
    return calls


def equivalent(a,b):
    return type(a) is type(b) and a==b


def expected_match(calls,case):
    if len(calls)!=1 or calls[0].get('name')!=case['tool']:return False
    args=calls[0].get('arguments')
    if not isinstance(args,dict):return False
    expected=case['expected_arguments']
    if any(k not in args or not equivalent(args[k],v) for k,v in expected.items()):return False
    extra=set(args)-set(expected)
    return not extra or (case['tool']=='edit_file' and extra=={'allow_multiple'} and args['allow_multiple'] is False)


def classify(case,raw,api_calls,finish_reason,has_token_ids=True):
    if finish_reason=='length':return {'label':'truncated','reason':'Output limit reached; do not attribute a parser fault.'}
    if not has_token_ids or raw is None:return {'label':'missing_raw_capture','reason':'Same-generation raw IDs/text unavailable.'}
    try:native=decode(raw)
    except ValueError as error:return {'label':'ambiguous','reason':str(error),'scope':'Independent decoder supports only strict flat native syntax.'}
    raw_ok=expected_match(native,case);api_ok=expected_match(api_calls,case)
    same=native==api_calls
    label='correct' if raw_ok and api_ok else ('parser_mismatch_suspected' if raw_ok and not api_ok else ('raw_output_defect' if same else 'ambiguous'))
    return {'label':label,'native_expected_match':raw_ok,'api_expected_match':api_ok,'native_equals_api':same,'independent_native_calls':native,
            'reason':'Comparison uses raw and parsed output from one generation; suspected mismatches still require engine/config review.'}
