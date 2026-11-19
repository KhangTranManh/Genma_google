"""Candidate scheduling definitions only; never accepts/rejects a patch by prediction."""
import hashlib,json

def prediction_map(hypothesis,catalog_ids):
    pairs=hypothesis['predictions']
    if len(pairs)!=len(catalog_ids) or {p['probe_id'] for p in pairs}!=set(catalog_ids):raise ValueError('Missing/duplicate/foreign probe ID')
    if any(p['expected'] not in ('fast','slow','uncertain') for p in pairs):raise ValueError('Invalid prediction')
    return {p['probe_id']:p['expected'] for p in pairs}

def signature(hypothesis,catalog_ids,version,phase):
    mapping=prediction_map(hypothesis,catalog_ids)
    return (version,phase,tuple((pid,mapping[pid]) for pid in sorted(catalog_ids)))

def behavior_groups(hypotheses,catalog_ids,version,phase):
    groups={}
    for h in hypotheses:groups.setdefault(signature(h,catalog_ids,version,phase),[]).append(h['id'])
    return list(groups.values())

def novelty(candidate,existing,catalog_ids,version,phase):
    s=signature(candidate,catalog_ids,version,phase);p=prediction_map(candidate,catalog_ids)
    return {'new_vector':all(s!=signature(h,catalog_ids,version,phase) for h in existing),'decisive_disagreement_with_every_existing':all(any(p[pid] in ('fast','slow') and prediction_map(h,catalog_ids)[pid] in ('fast','slow') and p[pid]!=prediction_map(h,catalog_ids)[pid] for pid in catalog_ids) for h in existing) if existing else False}

def rank_only(hypotheses,catalog_ids,public_observations,known_public_ids):
    if not set(known_public_ids)<=set(catalog_ids):raise ValueError('Known evidence outside catalog')
    rows=[]
    for index,h in enumerate(hypotheses):
        pred=prediction_map(h,catalog_ids);matches=[];contradictions=[]
        for pid in known_public_ids:
            actual=public_observations[pid]['observed']
            if actual not in ('fast','slow') or pred[pid]=='uncertain':continue
            (matches if pred[pid]==actual else contradictions).append(pid)
        decisive=len(matches)+len(contradictions)
        severe=len(contradictions)>=3 and decisive>=4 and len(contradictions)/decisive>=0.75
        rows.append({'hypothesis':h,'input_order':index,'matches':matches,'contradictions':contradictions,'severe_flag':severe,'eligible':True})
    return sorted(rows,key=lambda r:(-len(r['matches']),len(r['contradictions']),-float(r['hypothesis'].get('ochiai_max',0)),r['input_order']))

def audit_metrics(records):
    """Only supplied completed/scorable labels; no hypothetical labels for skipped candidates."""
    complete=[r for r in records if r.get('attempt_status')=='scorable']
    if any(type(r.get('verified_patch_pass')) is not bool for r in complete):raise ValueError('Scorable attempts require an explicit boolean outcome')
    skipped=[r for r in complete if r['old_skipped']]
    successes=[r for r in complete if r.get('verified_patch_pass') is True]
    missed=[r for r in successes if r['old_skipped']]
    allowed=[r for r in complete if not r['old_skipped']]
    return {'planned':len(records),'scorable':len(complete),'missing_or_unrun':len(records)-len(complete),'skipped_scorable':len(skipped),'allowed_scorable':len(allowed),'verified_passes':len(successes),'missed_successes':len(missed),'missed_success_yield':len(missed)/len(skipped) if skipped else None,'false_negative_rate_among_successes':len(missed)/len(successes) if successes else None,'allowed_patch_yield':sum(r.get('verified_patch_pass') is True for r in allowed)/len(allowed) if allowed else None}

def compile_probe(proposal,seen_hashes=()):
    allowed={'hypothesis_a','hypothesis_b','segments','base_url','expected_for_a','expected_for_b','rationale'}
    if set(proposal)!=allowed:raise ValueError('Invalid proposal fields')
    if not all(isinstance(proposal[k],str) and proposal[k] for k in ['hypothesis_a','hypothesis_b','rationale']):raise ValueError('Missing IDs/rationale')
    if proposal['hypothesis_a']==proposal['hypothesis_b']:raise ValueError('Distinct hypotheses required')
    if len(proposal['rationale'])>512:raise ValueError('Rationale too long')
    a,b=proposal['expected_for_a'],proposal['expected_for_b']
    if a not in ('fast','slow') or b not in ('fast','slow') or a==b:raise ValueError('Opposite decisive predictions required')
    segments=proposal['segments'];base=proposal['base_url']
    if not isinstance(base,str) or len(base)>2048:raise ValueError('Invalid base URL')
    if not isinstance(segments,list) or not 1<=len(segments)<=8:raise ValueError('Segment budget')
    size=0
    for s in segments:
        if not isinstance(s,dict) or set(s)!={'literal','repeat'}:raise ValueError('Literal-only DSL')
        if not isinstance(s['literal'],str) or len(s['literal'])>256 or type(s['repeat']) is not int or not 1<=s['repeat']<=6000:raise ValueError('Invalid literal/repeat')
        size+=len(s['literal'].encode('utf-8'))*s['repeat']
    if size>131072:raise ValueError('UTF8 input budget')
    text=''.join(s['literal']*s['repeat'] for s in segments)
    fingerprint=hashlib.sha256(json.dumps({'text':text,'base_url':base},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if fingerprint in seen_hashes:raise ValueError('Previously used input')
    return {'text':text,'base_url':base,'input_sha256':fingerprint,'utf8_bytes':size}
