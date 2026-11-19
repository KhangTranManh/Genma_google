"""Trusted container-side diagnostic. Never included in model input."""
import subprocess,sys,json,statistics
SIZES=[2000,4000,8000,30000]
REPEATS=3
TIMEOUT_SECONDS=3
MAX_LARGE_MEDIAN=0.5
MAX_GROWTH=8
FLOOR_SECONDS=0.005
worker='''import time,json,sys
from w3lib.html import get_base_url
n=int(sys.argv[1]);text="<base "*n
start=time.perf_counter();result=get_base_url(text);elapsed=time.perf_counter()-start
assert result=="",repr(result)
print(json.dumps({"seconds":elapsed}))
'''
def main():
    timings={};error=None;timeouts=[]
    try:
        from w3lib.html import get_base_url
        for html,base,want in [('<base href="https://example.org/path/">','','https://example.org/path/'),("<BASE href='https://example.org/'>",'','https://example.org/'),('<base href="/assets/">','https://example.org/root','https://example.org/assets/'),('<p>plain text</p>','https://example.org/','https://example.org/'),('<!-- <base href="https://bad.example/"> -->','https://example.org/','https://example.org/')]:
            assert get_base_url(html,base)==want,(html,get_base_url(html,base),want)
        valid=True
    except Exception as e:valid=False;error=repr(e)
    for n in SIZES:
        samples=[]
        for _ in range(REPEATS):
            try:
                p=subprocess.run([sys.executable,'-c',worker,str(n)],capture_output=True,text=True,timeout=TIMEOUT_SECONDS)
                if p.returncode:raise RuntimeError(p.stderr)
                samples.append(json.loads(p.stdout)['seconds'])
            except subprocess.TimeoutExpired:timeouts.append(n);break
            except Exception as e:error=repr(e);break
        timings[str(n)]=samples
    med={k:statistics.median(v) for k,v in timings.items() if len(v)==REPEATS}
    growth=med.get('8000',float('inf'))/max(med.get('2000',0),FLOOR_SECONDS)
    performance=not timeouts and len(med)==len(SIZES) and med.get('30000',float('inf'))<=MAX_LARGE_MEDIAN and growth<=MAX_GROWTH
    result={'valid_url_checks_pass':valid,'performance_pass':performance,'passed':bool(valid and performance and error is None),'timings':timings,'medians':med,'growth_8k_over_2k_floored':growth if growth!=float('inf') else None,'timeouts':timeouts,'error':error,'thresholds':{'sizes':SIZES,'repeats':REPEATS,'timeout_seconds':TIMEOUT_SECONDS,'large_median_max':MAX_LARGE_MEDIAN,'growth_max':MAX_GROWTH,'denominator_floor':FLOOR_SECONDS}}
    print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
