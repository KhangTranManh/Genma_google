import unittest,importlib.util
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'scripts/revise_hyp/policy.py';spec=importlib.util.spec_from_file_location('revise_hyp_policy',path);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OBS={pid:{'observed':v} for pid,v in zip(p.PROBE_IDS,['slow','fast','fast','fast','slow','fast'])}
def h(values):return {'id':'H','filepath':'w3lib/html.py','start_line':25,'end_line':27,'predictions':[{'probe_id':pid,'expected':v} for pid,v in zip(p.PROBE_IDS,values)]}
class Tests(unittest.TestCase):
 def test_copying_old_results_insufficient(self):self.assertFalse(p.assess_predictions(h(['slow','fast','fast','fast','uncertain','uncertain']),OBS)['eligible'])
 def test_transfer_contradiction_blocks(self):self.assertFalse(p.assess_predictions(h(['slow','fast','fast','fast','fast','fast']),OBS)['eligible'])
 def test_transfer_match_eligible(self):self.assertTrue(p.assess_predictions(h(['slow','fast','fast','fast','slow','uncertain']),OBS)['eligible'])
 def test_gray_measurement_not_decisive_match(self):
  obs={**OBS,'repeated_open_then_close':{'observed':'uncertain'}}
  self.assertFalse(p.assess_predictions(h(['slow','fast','fast','fast','slow','uncertain']),obs)['eligible'])
 def test_revision_disclosure_excludes_new_outcomes(self):
  known=p.disclose_training_probes(OBS);self.assertEqual(set(known),set(p.PROBE_IDS[:4]));self.assertNotIn('repeated_open_then_close',known)
 def test_duplicate_probe_invalid(self):
  value=h(['slow','fast','fast','fast','slow','fast']);value['predictions'][-1]['probe_id']='plain_text'
  with self.assertRaises(ValueError):p.assess_predictions(value,OBS)
if __name__=='__main__':unittest.main()
