"""Container-side objective observations; no model judges acceptance."""
import json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path

def semantic(lengths):
    from w3lib.html import get_base_url
    results=[]
    for n in lengths:
        text='<base data-extra="'+'x'*n+'" href="https://example.org/path/">'
        actual=get_base_url(text)
        results.append({'attribute_length':n,'passed':actual=='https://example.org/path/','actual':actual})
    return results

def main():
    perf=subprocess.run([sys.executable,'/tmp/role_perf.py'],capture_output=True,text=True,timeout=20)
    try:p=json.loads(perf.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):p={'passed':False,'error':'Missing performance result'}
    tests=subprocess.run([sys.executable,'-m','pytest','tests/test_html.py','-q','--junitxml=/tmp/role-tests.xml'],capture_output=True,text=True,timeout=70)
    Path('/tmp/role-tests-output.txt').write_text(tests.stdout+'\n'+tests.stderr)
    counts={'tests':0,'failures':0,'errors':0,'skipped':0}
    try:
        root=ET.parse('/tmp/role-tests.xml').getroot()
        for suite in root.iter('testsuite'):
            for key in counts:counts[key]+=int(suite.attrib.get(key,0))
        valid=counts['tests']>0 and tests.returncode in [0,1,2]
    except Exception:valid=False
    try:checks=semantic([0,200,1000]);sem=all(c['passed'] for c in checks)
    except Exception as e:checks=[{'passed':False,'error':repr(e)}];sem=False
    result={'performance':p,'functional':dict(counts,exit_code=tests.returncode,valid_result=valid),'semantic_guard':{'passed':sem,'cases':checks},'infrastructure_error':bool(p.get('error')=='Missing performance result' or not valid)}
    result['failure_count']=int(not p.get('passed',False))+counts['failures']+counts['errors']+sum(not c['passed'] for c in checks)
    result['passed']=bool(not result['infrastructure_error'] and p.get('passed') and valid and tests.returncode==0 and sem)
    print(json.dumps(result))
if __name__=='__main__':main()
