"""Public diagnostic; output may be shown to model. Independent grader stays hidden."""
import subprocess,sys,json,statistics
code='''from w3lib.html import get_base_url
import time,json
s="<base "*6000
start=time.perf_counter();r=get_base_url(s);elapsed=time.perf_counter()-start
assert r=="",repr(r)
print(json.dumps({"seconds":elapsed}))'''
def main():
    samples=[];error=None;timed_out=False
    for _ in range(3):
        try:
            p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=2)
            if p.returncode:raise RuntimeError(p.stderr)
            samples.append(json.loads(p.stdout)['seconds'])
        except subprocess.TimeoutExpired:timed_out=True;break
        except Exception as e:error=str(e);break
    median=statistics.median(samples) if samples else None
    print(json.dumps({'reproducer':'get_base_url("<base " * 6000)','measure':'function time only, excluding Python startup','samples_seconds':samples,'median_seconds':median,'timeout_seconds':2,'median_limit_seconds':0.2,'timed_out':timed_out,'error':error,'passed':len(samples)==3 and median<=0.2 and not timed_out and error is None}))
if __name__=='__main__':main()
