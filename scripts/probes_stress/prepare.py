"""Export one shared schema set; preserve the previous eight captures unchanged."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[2]


def prepare():
    from google.adk.tools.skill_toolset import RunSkillScriptTool
    from google.adk.models.lite_llm import _function_declaration_to_tool_param
    folder=ROOT/'experiments/toolcall_stress_v1'
    tools=json.loads((ROOT/'experiments/toolcall_probe_v1/tools.json').read_text())
    tools.append(_function_declaration_to_tool_param(RunSkillScriptTool(None)._get_declaration()))
    direct=json.loads((ROOT/'experiments/toolcall_probe_v1/cases.json').read_text())
    for c in direct:c['pair_reference']=c['id']
    skill=[]
    for operation,reference in [('read','read_range'),('test','run_test_command')]:
        for encoding in ['list','object']:
            options={'path':'src/example.py','start':17,'end':31} if operation=='read' else {'path':'tests/test_example.py'}
            argv=[operation]
            for k,v in options.items():argv+=['--'+k,str(v)]
            arguments={'skill_name':'bounded-workspace','file_path':'scripts/workspace_ops.py','args':argv if encoding=='list' else options}
            if encoding=='object':arguments['positional_args']=[operation]
            skill.append({'id':operation+'_'+encoding,'tool':'run_skill_script','expected_arguments':arguments,'pair_reference':reference,
                          'instruction':'The skill bounded-workspace is already available for this formatting probe. Emit exactly one run_skill_script call with these argument values: '+json.dumps(arguments,ensure_ascii=False)+'. Do not execute the script or invent a result.'})
    cases={'short_direct':direct,'long_direct':direct,'short_skill':skill}
    (folder/'tools.json').write_text(json.dumps(tools,indent=2)+'\n')
    (folder/'cases.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False)+'\n')
    definition={'status':'prepared','expected_requests':24,'schema_count':len(tools),'same_toolset_all_arms':True,
                'tools_sha256':hashlib.sha256((folder/'tools.json').read_bytes()).hexdigest(),
                'comparison_rules':['long_direct vs short_direct: identical task and schema, synthetic background padding only',
                                    'short_skill vs mapped short_direct: same read/test intent, different interface bundle; not a pure nesting-only causal estimate',
                                    'Do not compare aggregate short_skill accuracy against four different direct tasks.'],
                'old_cohort':'runs/toolcall-probe-v1 kept unchanged'}
    (ROOT/'reports/toolcall-stress-v1/definition.json').write_text(json.dumps(definition,indent=2)+'\n')

if __name__=='__main__':prepare()
