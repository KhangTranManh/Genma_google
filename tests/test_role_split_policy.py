import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/role_split'))
from policy import rank,decision

def obs(failures=1,passed=False,semantic=True,functional=0,infrastructure=False):return {'failure_count':failures,'passed':passed,'semantic_guard':{'passed':semantic},'functional':{'failures':functional,'errors':0},'performance':{'passed':passed},'infrastructure_error':infrastructure}
class PolicyTests(unittest.TestCase):
 def test_objective_pass_retained(self):self.assertTrue(decision(obs(),obs(0,True),'diff',set())['retain'])
 def test_regression_not_retained(self):self.assertFalse(decision(obs(3),obs(2,False,functional=1),'diff',set())['retain'])
 def test_semantic_guard_overrides_progress(self):self.assertFalse(decision(obs(),obs(0,True,False),'diff',set())['retain'])
 def test_duplicate_excluded(self):
  d=decision(obs(),obs(0,True),'diff',set());self.assertFalse(decision(obs(),obs(0,True),'diff',{d['diff_sha256']})['retain'])
 def test_infrastructure_inconclusive(self):self.assertEqual(decision(obs(),obs(0,True,infrastructure=True),'diff',set())['reason'],'inconclusive_infrastructure')
 def test_ochiai_and_tie_order(self):
  hyps=[{'id':'A','filepath':'w3lib/html.py','start_line':10,'end_line':10},{'id':'B','filepath':'w3lib/html.py','start_line':20,'end_line':20},{'id':'C','filepath':'w3lib/html.py','start_line':20,'end_line':20}]
  r=rank(hyps,{'failing_covered_lines':[10,20],'passing_covered_lines':[[10],[]]},obs())
  self.assertEqual([x['hypothesis']['id'] for x in r],['B','C','A']);self.assertEqual(r[0]['ochiai_max'],1)
if __name__=='__main__':unittest.main()
