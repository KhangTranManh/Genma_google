"""Evaluator-only policy replay on fixed measured candidates; no inference/selection feedback."""
from pathlib import Path
import json
from policies import rank_only,behavior_groups
ROOT=Path(__file__).resolve().parents[2]
def main():
    out=ROOT/'reports/gate-review-v1';data=json.loads((out/'audit-results.json').read_text());records=data['records']
    if any(r['attempt_status']!='scorable' for r in records):raise RuntimeError('Incomplete pool, cannot replay as complete')
    results=[];groups=[]
    for trajectory in sorted({r['trajectory'] for r in records}):
        rows=[r for r in records if r['trajectory']==trajectory];sample=rows[0];ranking=json.loads((ROOT/sample['source_ranking']).read_text());observed=ranking['original_probe_observations'];ids=sorted(observed);hypotheses=[r['hypothesis'] for r in rows]
        by_id={r['hypothesis']['id']:r for r in rows}
        if len(by_id)!=len(rows):raise ValueError('Duplicate IDs within trajectory')
        soft=rank_only(hypotheses,ids,observed,ids)
        order={'original_order':[r['hypothesis']['id'] for r in sorted(rows,key=lambda r:ranking['entries'][r['source_index']]['input_order'])],'old_gate':[r['hypothesis']['id'] for r in rows if not r['old_skipped']],'rank_only':[r['hypothesis']['id'] for r in soft]}
        for policy,queue in order.items():
            for budget in [1,2,3]:
                tried=queue[:budget];results.append({'trajectory':trajectory,'policy':policy,'patch_budget':budget,'attempted_ids':tried,'actual_attempts':len(tried),'any_verified_pass':any(by_id[i]['verified_patch_pass'] for i in tried)})
        groups.append({'trajectory':trajectory,'hypothesis_ids':len(rows),'unique_prediction_vectors':len(behavior_groups(hypotheses,ids,sample['source_run'],'gate_decision')),'groups':behavior_groups(hypotheses,ids,sample['source_run'],'gate_decision'),'new_hypothesis_request_run':False})
    result={'status':'offline_replay_only','candidate_generation_repeated':False,'ranking_evidence_phase':'diagnostic outcomes known at original gate decision, not independent final grader','budgets':[1,2,3],'records':results,'behavior_groups':groups}
    (out/'policy-replay.json').write_text(json.dumps(result,indent=2)+'\n');print('Replayed',len(results),'trajectory/policy/budget conditions; no inference.')
if __name__=='__main__':main()
