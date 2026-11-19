from pathlib import Path
import copy
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/probes_stress'))
from native_nested import decode,classify,expected
from length_calibration import extend

class StressDefinitionTests(unittest.TestCase):
    def test_separate_arms_share_direct_cases_and_only_nested_cases_map_to_controls(self):
        cases=json.loads((ROOT/'experiments/toolcall_stress_v1/cases.json').read_text())
        self.assertEqual(cases['short_direct'],cases['long_direct'])
        self.assertEqual(sum(len(c) for c in cases.values())*2,24)
        self.assertEqual({c['tool'] for c in cases['short_skill']},{'run_skill_script'})
        self.assertEqual({c['pair_reference'] for c in cases['short_skill']},{'read_range','run_test_command'})
        tools=json.loads((ROOT/'experiments/toolcall_stress_v1/tools.json').read_text());self.assertEqual(len(tools),5)
    def test_independent_decoder_preserves_nested_arrays_and_objects(self):
        raw='<|tool_call>call:run_skill_script{skill_name:<|"|>bounded-workspace<|"|>,file_path:<|"|>scripts/workspace_ops.py<|"|>,args:{path:<|"|>src/example.py<|"|>,start:17,end:31},positional_args:[<|"|>read<|"|>]}<tool_call|>'
        case=next(c for c in json.loads((ROOT/'experiments/toolcall_stress_v1/cases.json').read_text())['short_skill'] if c['id']=='read_object')
        calls=decode(raw);self.assertTrue(expected(calls,case));self.assertEqual(classify(case,raw,calls,'tool_calls')['label'],'correct')
        calls[0]['arguments']['args']['start']='17';self.assertFalse(expected(calls,case))
    def test_malformed_embedded_field_is_observed_in_raw_not_blame_parser(self):
        raw='<|tool_call>call:run_skill_script{file_path:<|"|>scripts/workspace_ops.py`,skill_name:bounded-workspace<|"|>,args:[<|"|>read<|"|>]}<tool_call|>'
        calls=decode(raw);self.assertNotIn('skill_name',calls[0]['arguments'])
        case={'tool':'run_skill_script','expected_arguments':{'skill_name':'bounded-workspace'}}
        self.assertEqual(classify(case,raw,calls,'tool_calls')['label'],'raw_output_defect')
    def test_length_padding_preserves_task_and_does_not_mutate_original(self):
        class Tokenizer:
            def encode(self,t,**kw):return list(t)
            def decode(self,t,**kw):return ''.join(t)
        request={'model':'fixture','messages':[{'role':'system','content':'system'},{'role':'user','content':'FINAL_TASK'}],'tools':[],'chat_template_kwargs':{}}
        before=copy.deepcopy(request)
        result,measurement=extend(request,Tokenizer(),target=1000,tolerance=0,counter=lambda x:sum(len(m['content']) for m in x['messages']))
        self.assertEqual(request,before);self.assertEqual(measurement['measured_prompt_tokens'],1000)
        self.assertTrue(result['messages'][-1]['content'].endswith('FINAL_TASK'))

if __name__=='__main__':unittest.main()
