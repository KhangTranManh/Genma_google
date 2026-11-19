from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/probes'))
from native_flat import decode,classify,expected_match

class NativeProbeTests(unittest.TestCase):
    def test_native_fields_preserve_quotes_newlines_and_numeric_types(self):
        raw='<|tool_call>call:write_file{filepath:<|"|>x.py<|"|>,content:<|"|>message = "hello"\nprint(message)\n<|"|>}<tool_call|>'
        c=decode(raw);self.assertEqual(c[0]['arguments']['content'],'message = "hello"\nprint(message)\n')
        numeric=decode('<|tool_call>call:read_file{filepath:<|"|>x.py<|"|>,start_line:17,end_line:31}<tool_call|>')
        self.assertIs(type(numeric[0]['arguments']['start_line']),int)
    def test_field_name_embedded_in_string_is_not_invented_as_a_field(self):
        raw='<|tool_call>call:write_file{content:<|"|>hello`,filepath:x.py<|"|>}<tool_call|>'
        c=decode(raw);self.assertNotIn('filepath',c[0]['arguments'])
        case={'tool':'write_file','expected_arguments':{'filepath':'x.py','content':'hello'}}
        self.assertEqual(classify(case,raw,c,'tool_calls')['label'],'raw_output_defect')
    def test_raw_correct_but_api_field_missing_is_only_suspected_parser_mismatch(self):
        raw='<|tool_call>call:read_file{filepath:<|"|>x.py<|"|>,start_line:17}<tool_call|>'
        case={'tool':'read_file','expected_arguments':{'filepath':'x.py','start_line':17}}
        api=[{'name':'read_file','arguments':{'filepath':'x.py'}}]
        self.assertEqual(classify(case,raw,api,'tool_calls')['label'],'parser_mismatch_suspected')
    def test_missing_or_truncated_capture_never_blames_parser(self):
        case={'tool':'read_file','expected_arguments':{}}
        self.assertEqual(classify(case,None,[],'stop',False)['label'],'missing_raw_capture')
        self.assertEqual(classify(case,'partial',[],'length')['label'],'truncated')
        self.assertEqual(classify(case,'unsupported',[],'stop')['label'],'ambiguous')
    def test_optional_default_is_accepted_but_numeric_string_is_not(self):
        case={'tool':'edit_file','expected_arguments':{'filepath':'x','old_string':'a','new_string':'b'}}
        self.assertTrue(expected_match([{'name':'edit_file','arguments':dict(case['expected_arguments'],allow_multiple=False)}],case))
        self.assertFalse(expected_match([{'name':'read_file','arguments':{'start_line':'17'}}],{'tool':'read_file','expected_arguments':{'start_line':17}}))

if __name__=='__main__':unittest.main()
