"""One agent, six direct tools; separately saved simple and flat control arms."""
from pathlib import Path
import shutil
import json
ROOT=Path(__file__).resolve().parents[2]

def build():
    rows=[]
    for model in ['12b','31b']:
        for arm in ['simple','control']:
            target=ROOT/'submission_candidates/simple_v1'/arm/model
            if target.exists():raise FileExistsError('Preserve prior candidates; use a new version')
            shutil.copytree(ROOT/'submission_candidates/reading_v1/prompt'/model,target)
            if arm=='simple':shutil.copyfile(ROOT/'experiments/prompts/simple_v1/system.md',target/'prompts/system.md')
            rows.append({'model':model,'arm':arm,'path':str(target.relative_to(ROOT))})
    report=ROOT/'reports/simple-v1';report.mkdir(parents=True,exist_ok=True)
    (report/'definition.json').write_text(json.dumps({'candidates':rows,'scope':'Four synthetic tool diagnostics, then 12 paired real-issue development trials.'},indent=2)+'\n')
if __name__=='__main__':build()
