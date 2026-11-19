"""Prepare first-step tool-call diagnostics; never sends inference requests."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]

CASES=[
 {'id':'read_range','tool':'read_file','expected_arguments':{'filepath':'src/example.py','start_line':17,'end_line':31},
  'instruction':'Call read_file exactly once for src/example.py, from line 17 through line 31. Do not execute or invent a tool result.'},
 {'id':'write_quotes_newlines','tool':'write_file','expected_arguments':{'filepath':'scratch/example.py','content':'message = "hello"\nprint(message)\n'},
  'instruction':'Call write_file exactly once. filepath must be scratch/example.py. content must contain these two Python lines, each followed by a newline: message = "hello" and print(message). Do not claim the file was written.'},
 {'id':'edit_exact_line','tool':'edit_file','expected_arguments':{'filepath':'src/example.py','old_string':'    return value - 1','new_string':'    return value + 1'},
  'instruction':'Call edit_file exactly once for src/example.py. Replace the string consisting of four spaces followed by return value - 1 with four spaces followed by return value + 1. Do not execute or invent a tool result.'},
 {'id':'run_test_command','tool':'run_command','expected_arguments':{'command':'python -m pytest tests/test_example.py -q'},
  'instruction':'Call run_command exactly once with command exactly python -m pytest tests/test_example.py -q. Do not execute the command or invent its output.'}]


def prepare(root=ROOT):
    from google.adk.tools.function_tool import FunctionTool
    from google.adk.models.lite_llm import _function_declaration_to_tool_param
    from swegemma.context import SwegemmaContext
    tools=SwegemmaContext().create_tools()
    exported=[_function_declaration_to_tool_param(FunctionTool(func=tools[name])._get_declaration()) for name in ['read_file','write_file','edit_file','run_command']]
    folder=root/'experiments/toolcall_probe_v1';folder.mkdir(parents=True,exist_ok=True)
    (folder/'cases.json').write_text(json.dumps(CASES,indent=2,ensure_ascii=False)+'\n')
    (folder/'tools.json').write_text(json.dumps(exported,indent=2)+'\n')
    versions={name:importlib.metadata.version(name) for name in ['google-adk','swegemma','adk-submission','litellm']}
    result={'status':'defined_not_executed','case_count':len(CASES),'schema_versions':versions,
            'schemas_sha256':hashlib.sha256((folder/'tools.json').read_bytes()).hexdigest(),
            'inference_requests_sent':0,'tools_executed':0,
            'same_generation_capture':'Use return_token_ids=true with native auto tool parsing, then decode with the checkpoint tokenizer and skip_special_tokens=false.'}
    (root/'reports/toolcall-probe-v1/definition.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':print(json.dumps(prepare(),indent=2))
