"""Complete deterministic no-selection bookkeeping after the archived optional review truncation.
Never regenerate/reinterpret model output or choose rejected patches.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
    base=ROOT/'runs/role-probes-v1';state=json.loads((base/'state.json').read_text())
    if state['status']!='needs_review' or state.get('error')!="RuntimeError('feedback truncated; keep artifacts for review')":raise RuntimeError('Unexpected recovery state')
    pending=base/'31b/role_split/hypothesis_0/review';response=json.loads((pending/'response.json').read_text())
    if response['choices'][0]['finish_reason']!='length':raise RuntimeError('Expected archived truncation')
    save(base/'state-before-optional-review-finalization.json',state)
    save(pending/'unavailable.json',{'status':'unavailable','error':'Structured review truncated with repeated whitespace; no verdict accepted','used_for_selection':False})
    completed=[]
    for model in state['model_order']:
        directory=base/model;ranked=json.loads((directory/'ranking.json').read_text())['entries']
        for index,row in enumerate(ranked):
            if row['patch_gate']=='patch_representative':
                folder=directory/'role_split'/f'hypothesis_{index}';policy=json.loads((folder/'policy.json').read_text());json.loads((folder/'execution.json').read_text())
                if policy['retain']:raise RuntimeError('Retained candidate needs independent selection/grade; cannot finalize as none')
                completed.append({'model':model,'candidate':index,'retain':False,'reason':policy['reason'],'review_available':(folder/'review/result.json').exists()})
            else:completed.append({'model':model,'candidate':index,'retain':False,'reason':row['patch_gate'],'hypothesis':row['hypothesis']['id']})
        selection={'retained':[],'selected':None,'rule':'No public-pass candidate; model review never controls selection','no_patch_submitted':True}
        target=directory/'selection.json'
        if target.exists():
            old=json.loads(target.read_text())
            if old['selected'] is not None or old['retained']:raise RuntimeError('Unexpected prior selection')
        else:save(target,selection)
    state.update(status='complete_with_unavailable_feedback',completed=completed,advisory_review_error=state.pop('error'),finalization='Deterministic decisions complete; no model retry, no inferred partial verdict, no retained patch')
    save(base/'state.json',state)
if __name__=='__main__':main()
