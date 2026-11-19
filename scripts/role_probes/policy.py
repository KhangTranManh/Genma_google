import math,hashlib

def rank(hypotheses,coverage,baseline):
    fail=set(coverage['failing_covered_lines']);passes=[set(x) for x in coverage['passing_covered_lines']];rows=[]
    for index,h in enumerate(hypotheses):
        span=set(range(h['start_line'],h['end_line']+1)) if h['filepath']=='w3lib/html.py' else set()
        hits=span&fail
        scores={line:1/math.sqrt(1+sum(line in s for s in passes)) for line in hits}
        rows.append({'hypothesis':h,'input_order':index,'reproducer_fails_baseline':not baseline['performance']['passed'],'fail_coverage_hits':sorted(hits),'ochiai_max':max(scores.values(),default=0),'sbfl_available':True,'exception_stack_trace_available':False})
    return sorted(rows,key=lambda x:(not x['reproducer_fails_baseline'],-x['ochiai_max'],x['input_order']))

def decision(baseline,observed,diff,seen):
    fingerprint=hashlib.sha256(diff.encode()).hexdigest()
    duplicate=bool(diff and fingerprint in seen)
    infrastructure=bool(observed.get('infrastructure_error'))
    no_regression=observed['functional']['failures']+observed['functional']['errors']<=baseline['functional']['failures']+baseline['functional']['errors'] and observed['semantic_guard']['passed']
    progressed=not infrastructure and no_regression and observed['failure_count']<baseline['failure_count']
    retain=bool(diff and not duplicate and progressed and observed['passed'])
    return {'retain':retain,'progressed':progressed,'no_regression':no_regression,'duplicate_diff':duplicate,'diff_sha256':fingerprint,'reason':'retain_objective_pass' if retain else ('inconclusive_infrastructure' if infrastructure else ('eliminate_duplicate' if duplicate else 'eliminate_no_verified_progress'))}

PROBE_IDS=('repeated_open','single_open','closed_tags','plain_text')
def assess_predictions(hypothesis,observed):
    predictions=hypothesis['predictions']
    if len(predictions)!=4 or {p['probe_id'] for p in predictions}!=set(PROBE_IDS):raise ValueError('Each catalog probe must appear exactly once')
    matched=[];contradicted=[];unknown=[]
    for p in predictions:
        actual=observed[p['probe_id']]['observed']
        if p['expected']=='uncertain' or actual=='uncertain':unknown.append(p['probe_id'])
        elif p['expected']==actual:matched.append(p['probe_id'])
        else:contradicted.append(p['probe_id'])
    return {'matched':matched,'contradicted':contradicted,'unknown':unknown,'eligible':bool('repeated_open' in matched and len(matched)>=2 and not contradicted),'prediction_status':'contradicted' if contradicted else ('consistent_not_proven' if matched else 'uncertain')}

def discriminated(a,b,observed):
    x={p['probe_id']:p['expected'] for p in a['predictions']};y={p['probe_id']:p['expected'] for p in b['predictions']}
    return [pid for pid in PROBE_IDS if observed[pid]['observed']!='uncertain' and x[pid] in ('fast','slow') and y[pid] in ('fast','slow') and x[pid]!=y[pid]]

def probe_rank(hypotheses,coverage,baseline,observed):
    entries=rank(hypotheses,coverage,baseline)
    for row in entries:row['probe_assessment']=assess_predictions(row['hypothesis'],observed)
    entries.sort(key=lambda r:(not r['probe_assessment']['eligible'],len(r['probe_assessment']['contradicted']),-len(r['probe_assessment']['matched']),-r['ochiai_max'],r['input_order']))
    representatives=[]
    for row in entries:
        if not row['probe_assessment']['eligible']:row['patch_gate']='skip_contradicted_or_uninformative';continue
        equivalent=next((r for r in representatives if not discriminated(row['hypothesis'],r['hypothesis'],observed)),None)
        if equivalent is not None:row.update(patch_gate='skip_not_distinguished',represented_by=equivalent['hypothesis']['id'])
        else:row['patch_gate']='patch_representative';representatives.append(row)
    return entries
