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
