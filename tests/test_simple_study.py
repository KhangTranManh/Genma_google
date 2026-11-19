import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/simple'))
from worker import jobs
from simple_report import generate

class SimpleStudyTests(unittest.TestCase):
    def test_direct_candidates_keep_all_other_settings_and_tools(self):
        for model in ['12b','31b']:
            simple=ROOT/'submission_candidates/simple_v1/simple'/model
            control=ROOT/'submission_candidates/simple_v1/control'/model
            def files(folder):return {str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            a,b=files(simple),files(control)
            self.assertEqual(a.keys(),b.keys());self.assertEqual({k for k in a if a[k]!=b[k]},{'prompts/system.md'})
            self.assertNotIn('Skill', (simple/'agent.yaml').read_text())
            self.assertLess(len(a['prompts/system.md']),len(b['prompts/system.md']))
    def test_queue_runs_four_micro_cases_before_twelve_real_cases(self):
        plan=tomllib.loads((ROOT/'configs/simple-study.toml').read_text());queue=jobs(plan)
        self.assertEqual(len(queue),16)
        self.assertEqual([j['phase'] for j in queue[:4]],['micro']*4)
        self.assertTrue(all(j['phase']=='real' for j in queue[4:]))
        self.assertEqual(len({tuple(sorted(j.items())) for j in queue}),16)
    def test_report_does_not_mix_synthetic_and_real_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'configs').mkdir();(root/'configs/simple-study.toml').write_bytes((ROOT/'configs/simple-study.toml').read_bytes())
            folder=root/'runs/simple-v1/micro/12b/edit_existing';folder.mkdir(parents=True)
            (folder/'summary.json').write_text(json.dumps({'diagnostic_pass':True,'independent_pass':True,'explicit_submit':True}))
            result=generate(root)
            self.assertEqual(sum(r['status']=='pass' for r in result['micro']),1)
            self.assertTrue(all(r['status']=='pending' for r in result['real']))

if __name__=='__main__':unittest.main()
