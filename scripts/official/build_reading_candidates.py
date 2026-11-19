"""Define focused-reading candidates without mutating pilot submissions or running models."""
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

ROOT=Path(__file__).resolve().parents[2]


def build(root=ROOT):
    plan=tomllib.loads((root/'configs/reading-study.toml').read_text())
    baseline=(root/'experiments/prompts/tool_recovery_v1.md').read_text()
    addition=(root/'experiments/prompts/focused_reading_v1.md').read_text()
    rows=[]
    for arm in plan['arm_order']:
        for model in plan['models']:
            destination=root/'submission_candidates/reading_v1'/arm/model
            if destination.exists():
                # Rebuilding a candidate after evaluation must use a new version.
                raise FileExistsError(f'Candidate exists; preserve it and define a new version: {destination}')
            shutil.copytree(root/'submission_candidates'/model,destination)
            text=baseline
            if arm in ('prompt','skill'):
                text+=addition
            if arm=='skill':
                shutil.copytree(root/'experiments/skills/focused-repo-reading',destination/'skills/focused-repo-reading')
                with (destination/'agent.yaml').open('a') as stream:
                    stream.write('skills:\n  - skills/focused-repo-reading\n')
                text+='\nBefore your first repository inspection, call load_skill with skill_name="focused-repo-reading". Consult its references only when relevant; do not reload unchanged guidance without a reason.\n'
            (destination/'prompts/system.md').write_text(text)
            rows.append({'arm':arm,'model':model,'directory':str(destination.relative_to(root)),
                         'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),
                         'status':'defined_not_executed','has_adk_skill':arm=='skill'})
    folder=root/'reports/reading-v1';folder.mkdir(parents=True,exist_ok=True)
    result={'plan':'configs/reading-study.toml','status':'defined_not_executed','expected_runs':plan['expected_runs'],
            'candidates':rows,'scope':'Development tasks already observed; not held-out evaluation.'}
    (folder/'definition.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    print(json.dumps(build(),indent=2))
