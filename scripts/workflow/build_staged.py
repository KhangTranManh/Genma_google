"""Build a separate staged YAML candidate and matched flat reference per model."""
from pathlib import Path
import json
import shutil
ROOT=Path(__file__).resolve().parents[2]


def build(root=ROOT):
    records=[]
    for model in ['31b','12b']:
        for arm in ['flat','staged']:
            destination=root/'submission_candidates/staged_v1'/arm/model
            if destination.exists():raise FileExistsError('Preserve existing candidates; define a new version')
            source=root/'submission_candidates/reading_v1/prompt'/model
            shutil.copytree(source,destination)
            if arm=='staged':
                (destination/'sub_agents').mkdir()
                shutil.copytree(root/'experiments/skills/bounded-workspace',destination/'skills/bounded-workspace')
                for name in ['planner','editor','verifier','submitter']:
                    shutil.copyfile(root/'experiments/prompts/staged_v1'/f'{name}.md',destination/'prompts'/f'{name}.md')
                (destination/'agent.yaml').write_text('''agent_class: SequentialAgent
name: staged_repair
sub_agents:
  - config_path: sub_agents/planner.yaml
  - config_path: sub_agents/repair_cycle.yaml
  - config_path: sub_agents/submitter.yaml
''')
                (destination/'sub_agents/repair_cycle.yaml').write_text('''agent_class: LoopAgent
name: bounded_repair_cycle
max_iterations: 2
sub_agents:
  - config_path: sub_agents/editor.yaml
  - config_path: sub_agents/verifier.yaml
''')
                alias=f'gemma-4-{model}-it-qat-w4a16-ct'
                tools={'planner':[], 'editor':['edit_file','write_file','get_status'], 'verifier':['get_status'], 'submitter':['get_status','submit_patch']}
                outputs={'planner':'navigation_plan','editor':'patch_summary','verifier':'verification_summary','submitter':'completion_summary'}
                for name in tools:
                    text=f'''agent_class: LlmAgent
name: {name}
model: {alias}
instruction: !include prompts/{name}.md
generate_content_config: !include configs/sampling.yaml
output_key: {outputs[name]}
disallow_transfer_to_parent: true
disallow_transfer_to_peers: true
'''
                    # Includes are relative to the containing YAML: keep all files inside root.
                    (destination/'sub_agents/prompts').mkdir(exist_ok=True)
                    (destination/'sub_agents/configs').mkdir(exist_ok=True)
                    shutil.copyfile(destination/'prompts'/f'{name}.md',destination/'sub_agents/prompts'/f'{name}.md')
                    shutil.copyfile(destination/'configs/sampling.yaml',destination/'sub_agents/configs/sampling.yaml')
                    text+='tools: '+('[]\n' if not tools[name] else '\n'+''.join('  - '+tool+'\n' for tool in tools[name]))
                    if name in ('editor','verifier'):text+='skills:\n  - skills/bounded-workspace\n'
                    # Skill references resolve from submission root, unlike !include.
                    (destination/'sub_agents'/f'{name}.yaml').write_text(text)
            records.append({'model':model,'arm':arm,'path':str(destination.relative_to(root))})
    folder=root/'reports/staged-v1';folder.mkdir(parents=True,exist_ok=True)
    (folder/'definition.json').write_text(json.dumps({'status':'defined_not_executed','candidates':records},indent=2)+'\n')


if __name__=='__main__':build()
