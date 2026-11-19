import importlib.util,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'scripts/gate_review/policies.py';s=importlib.util.spec_from_file_location('gate_review_policy',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
IDS=['a','b','c','d']
def hyp(name,vals):return {'id':name,'predictions':[{'probe_id':pid,'expected':v} for pid,v in zip(IDS,vals)]}
def proposal():return {'hypothesis_a':'H1','hypothesis_b':'H2','segments':[{'literal':'<base ','repeat':6000}],'base_url':'','expected_for_a':'fast','expected_for_b':'slow','rationale':'Two frozen mechanisms predict different behavior.'}
class Tests(unittest.TestCase):
 def test_rank_keeps_even_all_strong_contradictions(self):
  obs={pid:{'observed':'fast'} for pid in IDS};rows=m.rank_only([hyp('H',['slow']*4)],IDS,obs,IDS)
  self.assertEqual(len(rows),1);self.assertTrue(rows[0]['severe_flag']);self.assertTrue(rows[0]['eligible'])
 def test_unrevealed_outcome_does_not_change_rank(self):
  obs={pid:{'observed':'fast'} for pid in IDS};h=[hyp('H1',['fast','slow','fast','fast']),hyp('H2',['slow','fast','fast','fast'])]
  a=m.rank_only(h,IDS,obs,['a']);obs['b']['observed']='slow';b=m.rank_only(h,IDS,obs,['a']);self.assertEqual(a,b)
 def test_exact_groups_ignore_names_and_json_order(self):
  a=hyp('A',['slow','fast','fast','fast']);b=hyp('B',['slow','fast','fast','fast']);b['predictions'].reverse()
  self.assertEqual(m.behavior_groups([a,b],IDS,'v1','initial'),[['A','B']])
 def test_compatible_is_not_duplicate(self):self.assertEqual(len(m.behavior_groups([hyp('A',['slow','uncertain','fast','fast']),hyp('B',['slow','fast','fast','fast'])],IDS,'v1','initial')),2)
 def test_uncertainty_change_not_decisive_diversity(self):
  n=m.novelty(hyp('B',['slow','fast','fast','fast']),[hyp('A',['slow','uncertain','fast','fast'])],IDS,'v1','initial');self.assertTrue(n['new_vector']);self.assertFalse(n['decisive_disagreement_with_every_existing'])
 def test_no_success_fnr_undefined(self):
  r=m.audit_metrics([{'attempt_status':'scorable','old_skipped':True,'verified_patch_pass':False}]);self.assertIsNone(r['false_negative_rate_among_successes']);self.assertEqual(r['missed_success_yield'],0)
 def test_counterfactual_success_is_counted(self):
  rows=[{'attempt_status':'scorable','old_skipped':True,'verified_patch_pass':True},{'attempt_status':'scorable','old_skipped':False,'verified_patch_pass':False},{'attempt_status':'infra_error','old_skipped':True,'verified_patch_pass':None}];r=m.audit_metrics(rows);self.assertEqual(r['false_negative_rate_among_successes'],1);self.assertEqual(r['skipped_scorable'],1);self.assertEqual(r['missing_or_unrun'],1)
 def test_missing_label_cannot_be_counted_as_failure(self):
  with self.assertRaises(ValueError):m.audit_metrics([{'attempt_status':'scorable','old_skipped':True,'verified_patch_pass':None}])
 def test_literal_dsl_and_repeated_probe_rejected(self):
  value=proposal();compiled=m.compile_probe(value);self.assertEqual(len(compiled['text']),36000)
  with self.assertRaises(ValueError):m.compile_probe(value,[compiled['input_sha256']])
 def test_probe_limits_precede_expansion(self):
  value=proposal();value['segments']=[{'literal':'x'*256,'repeat':6000}]
  with self.assertRaises(ValueError):m.compile_probe(value)
 def test_equal_expected_outcomes_not_distinguishing(self):
  value=proposal();value['expected_for_b']='fast'
  with self.assertRaises(ValueError):m.compile_probe(value)
 def test_audit_inventory_not_fabricated(self):
  d=json.loads((ROOT/'experiments/gate_review_v1/audit-manifest.json').read_text());self.assertEqual(len(d['records']),9);self.assertEqual(sum(x['old_skipped'] for x in d['records']),8);self.assertTrue(all(x['attempt_status']=='not_run' for x in d['records']))
if __name__=='__main__':unittest.main()
