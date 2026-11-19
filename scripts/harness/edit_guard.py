"""B1 edit guard: catch mechanical edit failures before they consume a repair attempt.

check_edit() is pure (no I/O). guarded_call() wraps a generation function: when the guard rejects a
call as noop, out_of_region, not_found or ambiguous (mechanical failures), it re-asks exactly once with a short host notice. The re-ask is not
counted as a repair attempt; both calls and the guard events are returned for logging.
Grader results are never included in the notice.
"""
from dataclasses import dataclass,field

RETRYABLE={'noop','out_of_region','not_found','ambiguous'}
ALLOWED_KEYS={'filepath','old_string','new_string','allow_multiple'}


@dataclass
class Region:
    """Editable span of the file: from the first start_marker to the following end_marker (exclusive)."""
    start_marker:str
    end_marker:str

    def bounds(self,source):
        a=source.find(self.start_marker)
        if a<0:return None
        b=source.find(self.end_marker,a+len(self.start_marker))
        return (a,b if b>=0 else len(source))


def check_edit(calls,source,filepath,region=None):
    """Return {'status': ok|invalid|not_found|ambiguous|noop|out_of_region, 'message': str, 'after': str|None}."""
    deduplicated=False
    if isinstance(calls,list) and len(calls)>1:
        last=calls[-1].get('arguments') if isinstance(calls[-1],dict) else None
        if not (isinstance(last,dict) and all(isinstance(last.get(k),str) for k in ('old_string','new_string'))):
            calls=calls[:-1]  # trailing call cut off by the output limit
    if isinstance(calls,list) and len(calls)>1 and all(c==calls[0] for c in calls):
        calls=calls[:1];deduplicated=True
    r=_check(calls,source,filepath,region)
    if deduplicated:r['deduplicated_identical_calls']=True
    return r


def _check(calls,source,filepath,region):
    if not isinstance(calls,list) or len(calls)!=1 or calls[0].get('name')!='edit_file':
        return {'status':'invalid','message':'Expected exactly one edit_file call.','after':None}
    a=calls[0].get('arguments')
    if not isinstance(a,dict) or a.get('filepath')!=filepath or not set(a)<=ALLOWED_KEYS or not all(isinstance(a.get(k),str) for k in ('old_string','new_string')) or not a['old_string']:
        return {'status':'invalid','message':f'edit_file needs filepath={filepath!r} and non-empty string old_string/new_string.','after':None}
    old,new=a['old_string'],a['new_string']
    if old==new:
        return {'status':'noop','message':'Your previous edit_file call had new_string identical to old_string, so nothing changed. Emit one edit_file call whose new_string differs from old_string.','after':None}
    count=source.count(old)
    if count==0:return {'status':'not_found','message':'old_string does not occur verbatim in the current source.','after':None}
    if count>1 and not a.get('allow_multiple'):return {'status':'ambiguous','message':'old_string occurs more than once; include more context.','after':None}
    if region is not None:
        bounds=region.bounds(source)
        if bounds is None:return {'status':'out_of_region','message':'The editable region marker is missing from the current source.','after':None}
        lo,hi=bounds;start=0
        while (i:=source.find(old,start))>=0:
            if i<lo or i+len(old)>hi:
                return {'status':'out_of_region','message':'The edit touches code outside the supplied source block. Change only the supplied block.','after':None}
            start=i+1
    after=source.replace(old,new) if a.get('allow_multiple') else source.replace(old,new,1)
    if after==source:return {'status':'noop','message':'The edit leaves the file unchanged. Emit an edit that changes the code.','after':None}
    return {'status':'ok','message':'','after':after}


@dataclass
class GuardedResult:
    calls:list
    check:dict
    events:list=field(default_factory=list)
    generations:int=1


def guarded_call(generate,source,filepath,region=None,max_reasks=1):
    """generate(notice: str|None) -> list of parsed calls. Re-asks at most max_reasks times on retryable failures."""
    calls=generate(None);check=check_edit(calls,source,filepath,region);events=[];n=1
    while check['status'] in RETRYABLE and len(events)<max_reasks:
        events.append({'generation':n,'status':check['status'],'calls':calls})
        calls=generate('Host notice (not a grader result): '+check['message']);n+=1
        check=check_edit(calls,source,filepath,region)
    if check['status'] in RETRYABLE:events.append({'generation':n,'status':check['status'],'calls':calls,'final':True})
    return GuardedResult(calls,check,events,n)


def check_edits(calls,source,filepath,regions,max_calls=4):
    """Multi-excerpt variant: apply up to max_calls edit_file calls sequentially; every edit must lie in one of
    the regions (evaluated on the source as it is when that edit applies). Identical duplicate calls and a
    trailing call cut off by the output limit are dropped first. Returns the first non-ok check, or ok with 'after'."""
    if not isinstance(calls,list) or not calls:return {'status':'invalid','message':'Expected at least one edit_file call.','after':None}
    last=calls[-1].get('arguments') if isinstance(calls[-1],dict) else None
    if len(calls)>1 and not (isinstance(last,dict) and all(isinstance(last.get(k),str) for k in ('old_string','new_string'))):calls=calls[:-1]
    unique=[]
    for c in calls:
        if c not in unique:unique.append(c)
    if len(unique)>max_calls:return {'status':'invalid','message':f'At most {max_calls} edit_file calls are allowed.','after':None}
    cur=source;applied=0
    for c in unique:
        last_check=None
        for region in regions:
            r=_check([c],cur,filepath,region)
            if r['status']=='ok':cur=r['after'];applied+=1;break
            last_check=r if last_check is None or last_check['status']=='out_of_region' else last_check
        else:
            return dict(last_check,applied_before_failure=applied)
    return {'status':'ok','message':'','after':cur,'n_edits':applied,'deduplicated_calls':len(calls)-len(unique)}
