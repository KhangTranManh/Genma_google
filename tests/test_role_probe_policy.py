import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/role_probes/policy.py';s=importlib.util.spec_from_file_location('role_probe_policy',p);policy=importlib.util.module_from_spec(s);s.loader.exec_module(policy)

def hyp(name,values):return {'id':name,'filepath':'w3lib/html.py','start_line':10,'end_line':10,'predictions':[{'probe_id':pid,'expected':value} for pid,value in zip(policy.PROBE_IDS,values)]}
OBS={pid:{'observed':v} for pid,v in zip(policy.PROBE_IDS,['slow','fast','fast','fast'])}
class Tests(unittest.TestCase):
 def test_consistent_not_proven(self):
  a=policy.assess_predictions(hyp('a',['slow','fast','fast','fast']),OBS);self.assertTrue(a['eligible']);self.assertEqual(a['prediction_status'],'consistent_not_proven')
 def test_contradiction_blocks_patch(self):self.assertFalse(policy.assess_predictions(hyp('a',['slow','slow','fast','fast']),OBS)['eligible'])
 def test_all_unknown_not_supported(self):self.assertFalse(policy.assess_predictions(hyp('a',['uncertain']*4),OBS)['eligible'])
 def test_gray_measurement_does_not_refute(self):
  obs={**OBS,'single_open':{'observed':'uncertain'}};self.assertTrue(policy.assess_predictions(hyp('a',['slow','slow','fast','fast']),obs)['eligible'])
 def test_repeated_probe_invalid(self):
  h=hyp('a',['slow','fast','fast','fast']);h['predictions'][1]['probe_id']='repeated_open'
  with self.assertRaises(ValueError):policy.assess_predictions(h,OBS)
 def test_non_distinguished_group_not_false(self):
  rows=policy.probe_rank([hyp('a',['slow','fast','fast','fast']),hyp('b',['slow','uncertain','fast','fast']),hyp('c',['slow','slow','fast','fast'])],{'failing_covered_lines':[10],'passing_covered_lines':[[10]]},{'performance':{'passed':False}},OBS)
  self.assertEqual([r['patch_gate'] for r in rows],['patch_representative','skip_not_distinguished','skip_contradicted_or_uninformative']);self.assertEqual(rows[1]['probe_assessment']['prediction_status'],'consistent_not_proven')
if __name__=='__main__':unittest.main()
