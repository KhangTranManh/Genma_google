import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/official'))
from reading_metrics import analyze
from reading_watch import inspect_log
from reading_worker import jobs,plan,freeze_inputs
from reading_report import generate

class ReadingExecutionTests(unittest.TestCase):
    def trace(self,steps):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        folder=Path(temp.name);(folder/'traces').mkdir();(folder/'traces/trace.json').write_text(json.dumps({'steps':steps}));return folder

    def step(self,name,args,response,seconds=1):
        return {'source':'agent','tool_calls':[{'function_name':name,'arguments':args,'extra':{'elapsed_s':seconds}}],
                'observation':{'content':json.dumps(response)},'metrics':{'prompt_tokens':10,'completion_tokens':2}}

    def test_repeats_count_successful_same_ranges_and_reset_after_edit(self):
        read=self.step('read_file',{'filepath':'src/a.py','start_line':1,'end_line':80},{'status':'ok','content':'source'})
        different=self.step('read_file',{'filepath':'src/a.py','start_line':81,'end_line':120},{'status':'ok','content':'other'})
        edit=self.step('edit_file',{'filepath':'src/a.py'},{'status':'ok'},seconds=9)
        folder=self.trace([read,read,different,edit,read])
        result=analyze(folder)
        self.assertEqual(result['repeated_identical_read_results'],1)
        self.assertEqual(result['bounded_read_requests'],4)
        self.assertEqual(result['first_successful_source_file_tool_seconds'],9)
        self.assertEqual(result['prompt_tokens_observed'],50)

    def test_errors_and_failed_skill_load_do_not_count_as_success(self):
        folder=self.trace([self.step('load_skill',{'skill_name':'missing'},{'error':'not found'}),
                           self.step('submit_patch',{}, {'status':'error','error_type':'BudgetExceeded'}),
                           self.step('read_file',{'filepath':'src/a.py`,start_line:400'},{'status':'error','error_type':'FileNotFound'})])
        result=analyze(folder)
        self.assertFalse(result['skill_loaded_observed'])
        self.assertFalse(result['explicit_nonempty_submission'])
        self.assertEqual(result['suspected_malformed_filepath_requests'],1)
        self.assertEqual(result['successful_read_results'],0)

    def test_valid_submission_and_skill_activation_are_observed(self):
        folder=self.trace([self.step('load_skill',{'skill_name':'reading'},{'skill_name':'reading','instructions':'inspect'}),
                           self.step('submit_patch',{}, {'status':'ok','patch_size':40})])
        result=analyze(folder)
        self.assertTrue(result['explicit_nonempty_submission']);self.assertTrue(result['skill_loaded_observed'])

    def test_missing_trace_is_not_reported_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            result=analyze(Path(d));self.assertIsNone(result['repeated_identical_read_results'])
            self.assertIsNone(result['explicit_nonempty_submission'])

    def test_live_parser_ignores_result_lines(self):
        log='\x1b[2m[ 7.0s]\x1b[0m 📖 read_file (src/a.py)\n[ 7.1s] ✓ read_file result\n[ 9.0s] 🔧 run_command git grep symbol\n'
        result=inspect_log(log)
        self.assertEqual(result['observed_log_requests'],{'read_file':1,'run_command':1})
        self.assertEqual(result['consecutive_read_requests'],0)

    def test_job_cells_are_unique_and_models_never_include_e4b(self):
        cells=jobs(plan())
        self.assertEqual(len(cells),18)
        self.assertEqual(len({tuple(sorted(c.items())) for c in cells}),18)
        self.assertEqual(cells[0],{'model':'12b','task':'w3lib_264','arm':'prompt'})
        self.assertEqual({c['model'] for c in cells},{'12b','31b'})

    def test_runtime_v2_retains_controls_except_context_and_records_separate_jobs(self):
        import reading_worker_v2
        original=plan();updated=reading_worker_v2.plan()
        differences={k for k in original['controls'] if original['controls'][k]!=updated['controls'][k]}
        self.assertEqual(differences,{'max_model_len'})
        self.assertEqual(updated['controls']['max_model_len'],16384)
        self.assertEqual(len(reading_worker_v2.jobs(updated)),18)
        self.assertEqual(reading_worker_v2.jobs(updated)[0]['model'],'31b')
        self.assertNotEqual(reading_worker_v2.BASE.name,'reading-v1')

    def test_fingerprint_detects_candidate_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'submission_candidates/reading_v1/prompt/12b/agent.yaml'
            p.parent.mkdir(parents=True);p.write_text('first')
            before=freeze_inputs(root);p.write_text('changed')
            self.assertNotEqual(before['sha256'],freeze_inputs(root)['sha256'])

    def test_test_pass_without_model_submit_is_not_autonomous_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'configs').mkdir();(root/'configs/reading-study.toml').write_bytes((ROOT/'configs/reading-study.toml').read_bytes())
            folder=root/'runs/reading-v1/12b/prompt/w3lib_264';folder.mkdir(parents=True)
            (folder/'summary.json').write_text(json.dumps({'resolved':True,'duration_seconds':1}))
            (folder/'traces').mkdir();(folder/'traces/trace.json').write_text(json.dumps({'steps':[]}))
            result=generate(root)
            row=next(r for r in result['rows'] if r['model']=='12b' and r['arm']=='prompt' and r['task']=='w3lib_264')
            self.assertEqual(row['status'],'pass');self.assertFalse(row['autonomous_pass'])
            self.assertEqual(sum(r['status']=='pending' for r in result['rows']),17)

if __name__=='__main__':unittest.main()
