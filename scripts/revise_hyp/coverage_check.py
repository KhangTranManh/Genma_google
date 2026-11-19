"""Coverage observed separately from uninstrumented timing; not exception stack traces."""
import trace,json
from pathlib import Path
from w3lib.html import get_base_url

def collect(text,base=''):
    tracer=trace.Trace(count=True,trace=False);tracer.runfunc(get_base_url,text,base)
    return {str(line) for (filename,line),count in tracer.results().counts.items() if Path(filename).resolve()==Path('/workspace/w3lib/html.py')}
def main():
    fail=collect('<base '*6000)
    inputs=[('<base href="https://example.org/">',''),("<BASE href='https://example.org/'>",''),('<base href="/a">','https://example.org/'),('<p>text</p>','https://example.org/'),('<!-- <base href="https://bad.example/"> -->','https://example.org/')]
    passes=[collect(t,b) for t,b in inputs]
    print(json.dumps({'file':'w3lib/html.py','failing_reproducer_input_size':6000,'failure_label_source':'separate uninstrumented public performance result; traced timing not used','failing_covered_lines':sorted(map(int,fail)),'passing_covered_lines':[sorted(map(int,s)) for s in passes],'exception_stack_trace':None}))
if __name__=='__main__':main()
