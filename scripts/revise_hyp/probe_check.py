"""Trusted fixed baseline probes; model supplies predictions, never executable code."""
import subprocess,sys,json,statistics
INPUTS={'repeated_open':'<base '*6000,'single_open':'<base '+'x'*6000,'closed_tags':'<base >'*6000,'plain_text':'x'*6000}
INPUTS.update({'repeated_open_then_close':'<base '*6000+'>','repeated_open_then_href':'<base '*6000+'href="https://example.org/path/">'})
WORKER='''import sys,json,time
from w3lib.html import get_base_url
s=json.loads(sys.stdin.read());start=time.perf_counter();r=get_base_url(s);elapsed=time.perf_counter()-start
print(json.dumps({"seconds":elapsed,"result":r}))
'''
def main():
    results={}
    for name,text in INPUTS.items():
        samples=[];values=[];timed_out=False;error=None
        for _ in range(3):
            try:
                p=subprocess.run([sys.executable,'-c',WORKER],input=json.dumps(text),capture_output=True,text=True,timeout=3)
                if p.returncode:raise RuntimeError(p.stderr)
                value=json.loads(p.stdout);samples.append(value['seconds']);values.append(value['result'])
            except subprocess.TimeoutExpired:timed_out=True;break
            except Exception as ex:error=repr(ex);break
        median=statistics.median(samples) if samples else None
        observed='uncertain' if error else ('slow' if timed_out or median is not None and median>=0.2 else ('fast' if len(samples)==3 and median<=0.05 else 'uncertain'))
        results[name]={'samples_seconds':samples,'median_seconds':median,'observed':observed,'timed_out':timed_out,'error':error,'returned_empty':all(x=='' for x in values) if values else None}
    print(json.dumps({'results':results,'thresholds':{'repeats':3,'timeout_seconds':3,'fast_max_seconds':0.05,'slow_min_seconds':0.2,'gray_zone':'uncertain'},'timing_scope':'function time excluding process startup; no source mutation'}))
if __name__=='__main__':main()
