"""Independent strict native decoder for flat and nested synthetic cases only."""
import re
DELIM='<|"|>'

class Reader:
    def __init__(self,text):self.text=text;self.i=0
    def ws(self):
        while self.i<len(self.text) and self.text[self.i].isspace():self.i+=1
    def value(self,depth=0):
        if depth>16:raise ValueError('Depth limit')
        self.ws()
        if self.text.startswith(DELIM,self.i):
            self.i+=len(DELIM);end=self.text.find(DELIM,self.i)
            if end<0:raise ValueError('Unclosed string')
            value=self.text[self.i:end];self.i=end+len(DELIM);return value
        if self.i<len(self.text) and self.text[self.i]=='{':return self.object(depth+1)
        if self.i<len(self.text) and self.text[self.i]=='[':
            self.i+=1;items=[];self.ws()
            if self.i<len(self.text) and self.text[self.i]==']':self.i+=1;return items
            while True:
                items.append(self.value(depth+1));self.ws()
                if self.i>=len(self.text):raise ValueError('Incomplete array')
                if self.text[self.i]==']':self.i+=1;return items
                if self.text[self.i]!=',':raise ValueError('Array separator missing')
                self.i+=1
        end=self.i
        while end<len(self.text) and self.text[end] not in ',}]':end+=1
        word=self.text[self.i:end].strip();self.i=end
        if re.fullmatch(r'-?\d+',word):return int(word)
        if word in ('true','false'):return word=='true'
        if word=='null':return None
        raise ValueError('Unsupported bare value')
    def object(self,depth=0):
        if self.text[self.i]!='{':raise ValueError('Object start missing')
        self.i+=1;result={};self.ws()
        if self.i<len(self.text) and self.text[self.i]=='}':self.i+=1;return result
        while True:
            self.ws();key=re.match(r'([A-Za-z_]\w*)\s*:',self.text[self.i:])
            if not key:raise ValueError('Unsupported native key')
            self.i+=key.end()
            if key[1] in result:raise ValueError('Duplicate key')
            result[key[1]]=self.value(depth+1);self.ws()
            if self.i>=len(self.text):raise ValueError('Incomplete object')
            if self.text[self.i]=='}':self.i+=1;return result
            if self.text[self.i]!=',':raise ValueError('Field separator missing')
            self.i+=1


def decode(raw):
    result=[];position=0
    while True:
        match=re.search(r'<\|tool_call>call:([A-Za-z_]\w*)\{',raw[position:])
        if not match:break
        reader=Reader(raw);reader.i=position+match.end()-1;arguments=reader.object();reader.ws()
        if not raw.startswith('<tool_call|>',reader.i):raise ValueError('Missing closing native token')
        result.append({'name':match[1],'arguments':arguments});position=reader.i+len('<tool_call|>')
    if not result:raise ValueError('No supported complete native call')
    return result


def equal(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b


def expected(calls,case):
    if len(calls)!=1 or calls[0].get('name')!=case['tool']:return False
    args=calls[0].get('arguments');want=case['expected_arguments']
    if not isinstance(args,dict) or any(k not in args or not equal(args[k],v) for k,v in want.items()):return False
    extras=set(args)-set(want)
    return not extras or (case['tool']=='edit_file' and extras=={'allow_multiple'} and args['allow_multiple'] is False)


def classify(case,raw,api,finish_reason,has_token_ids=True):
    if finish_reason=='length':return {'label':'truncated'}
    if not has_token_ids or raw is None:return {'label':'missing_raw_capture'}
    try:calls=decode(raw)
    except ValueError as e:return {'label':'ambiguous','reason':str(e),'decoder_scope':'strict native syntax subset only'}
    a=expected(calls,case);b=expected(api,case);same=equal(calls,api)
    label='correct' if a and b else ('parser_mismatch_suspected' if a and not b else ('raw_output_defect' if same else 'ambiguous'))
    return {'label':label,'native_expected_match':a,'api_expected_match':b,'native_equals_api':same,'independent_native_calls':calls}
