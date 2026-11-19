"""Short read-only observations; alerts never alter agent feedback or budgets."""
from datetime import datetime,timezone
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from reading_metrics import read
from reading_report import generate
ROOT=Path(__file__).resolve().parents[2]
ANSI=re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
EVENT=re.compile(r'\[\s*([\d.]+)s\]\s+(?:📖|🔧|🤖|✏️|📝|📚|🔍|🛠️|🧩|⚙️)\s+(read_file|run_command|write_file|edit_file|submit_patch|get_status|load_skill_resource|load_skill)\b(.*)')


def inspect_log(text):
    calls=[]
    for line in ANSI.sub('',text).splitlines():
        match=EVENT.search(line)
        if match:calls.append({'seconds':float(match[1]),'tool':match[2],'detail':match[3].strip()})
    counts=Counter(c['tool'] for c in calls)
    streak=0
    for call in reversed(calls):
        if call['tool']!='read_file':break
        streak+=1
    return {'observed_log_requests':dict(counts),'last_observed_request':calls[-1] if calls else None,
            'consecutive_read_requests':streak}


def main(version="v1"):
    base=ROOT/('runs/reading-'+version);base.mkdir(parents=True,exist_ok=True)
    state=read(base/'state.json');current=state.get('current') or {};alerts=[]
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'state':state.get('status'),
            'phase':state.get('phase'),'current':current,'alerts':alerts,
            'note':'Log-derived observations are partial; full ATIF analysis after completion. Alerts are passive, no agent feedback.'}
    if all(k in current for k in ('model','arm','task')) and state.get('in_progress'):
        folder=base/current['model']/current['arm']/current['task']
        logs=sorted((folder/'logs').glob('*.log'))
        if logs:
            result.update(inspect_log(logs[0].read_text(errors='replace')))
            quiet=datetime.now(timezone.utc).timestamp()-logs[0].stat().st_mtime
            result['log_quiet_seconds']=round(quiet,1)
            if result['consecutive_read_requests']>=8:alerts.append('At least eight consecutive read_file requests; review trajectory after ending, no mid-run intervention.')
            if quiet>300:alerts.append('Log quiet for >300s; inspect model/server health. This alone is not a timeout verdict.')
        elif state.get('phase')=='agent':result['waiting_for']='Task initialization / first log'
    if state.get('error'):alerts.append(state['error'])
    tmp=base/'live.json.tmp';tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');tmp.replace(base/'live.json')
    generate(ROOT,version=version)
    with (base/'observations.jsonl').open('a') as output:output.write(json.dumps(result,ensure_ascii=False)+'\n')
    if state.get('status') in ('complete','needs_review'):
        subprocess.run(['systemctl','stop','gemma-lab-reading-watch.timer' if version=='v1' else 'gemma-lab-reading-v2-watch.timer'],check=False)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v1','v2'],default='v1');args=parser.parse_args();main(args.version)
