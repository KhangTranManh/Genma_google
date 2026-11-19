import json
import importlib.util
from pathlib import Path
import tomllib
import unittest
ROOT=Path(__file__).resolve().parents[1]

class ToolcallProbeDefinitionTests(unittest.TestCase):
    def test_scope_stays_small_and_tools_are_not_executed(self):
        plan=tomllib.loads((ROOT/'configs/toolcall-probe.toml').read_text())
        self.assertEqual(plan['phase'],'ready_for_execution')
        self.assertEqual(plan['initial_requests'],len(plan['models'])*len(plan['cases']))
        self.assertFalse(plan['execute_tools']);self.assertFalse(plan['stream'])
        self.assertTrue(plan['return_token_ids']);self.assertFalse(plan['classification']['compare_separate_generations'])

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'),'schema check runs in .venv-official')
    def test_expected_arguments_match_exported_schemas_and_preserve_types(self):
        from jsonschema import Draft202012Validator
        cases=json.loads((ROOT/'experiments/toolcall_probe_v1/cases.json').read_text())
        tools={t['function']['name']:t['function']['parameters'] for t in json.loads((ROOT/'experiments/toolcall_probe_v1/tools.json').read_text())}
        self.assertEqual(len(cases),4)
        for case in cases:Draft202012Validator(tools[case['tool']]).validate(case['expected_arguments'])
        read=next(c for c in cases if c['id']=='read_range')
        self.assertIs(type(read['expected_arguments']['start_line']),int)
        write=next(c for c in cases if c['id']=='write_quotes_newlines')
        self.assertEqual(write['expected_arguments']['content'],'message = "hello"\nprint(message)\n')
        edit=next(c for c in cases if c['id']=='edit_exact_line')
        self.assertTrue(edit['expected_arguments']['old_string'].startswith('    '))

    def test_preparation_did_not_run_a_model_or_tools(self):
        data=json.loads((ROOT/'reports/toolcall-probe-v1/definition.json').read_text())
        self.assertEqual(data['inference_requests_sent'],0);self.assertEqual(data['tools_executed'],0)
        self.assertEqual(data['status'],'defined_not_executed')

if __name__=='__main__':unittest.main()
