#!/bin/bash
# Emit one line per new event: queue log lines, finished tasks in any generic/official run, preflight results, tracebacks.
cd "$(dirname "$0")/../.."
seen=/tmp/generic-watch-seen.txt; touch $seen
emit(){ grep -qxF "$1" $seen || { echo "$1"; echo "$1" >> $seen; }; }
while true; do
  [ -f runs/generic-queue.log ] && while read -r l; do emit "QUEUE $l"; done < runs/generic-queue.log
  for r in generic-rep1 generic-rep2 generic-dev20; do
    f=runs/$r/31b/state.json; [ -f $f ] || continue
    python3 - "$r" "$f" <<'PY' 2>/dev/null | while read -r l; do emit "$l"; done
import json,sys
r,f=sys.argv[1],sys.argv[2];d=json.load(open(f))
for x in d.get('results',[]):print(f"{r} {x['task']}: status={x.get('status')} loc={x.get('loc_hit_file')} repro={x.get('repro_valid')} selected={x.get('selected')} resolved={x.get('selected_resolved')} any={x.get('any_resolved')}")
if d.get('status')!='running':print(f"{r} RUN {d.get('status')} {d.get('error','')[:150]}")
PY
  done
  [ -f runs/generic-dev20-prepare.out ] && while read -r l; do emit "PREP $l"; done < runs/generic-dev20-prepare.out
  [ -f runs/official-generic-v1/31b/summary.json ] && python3 -c "
import json;d=json.load(open('runs/official-generic-v1/31b/summary.json'))
for r in d['results']:print('OFFICIAL',r['instance_id'],'resolved=',r.get('resolved'),'err=',str(r.get('error'))[:100])" 2>/dev/null | while read -r l; do emit "$l"; done
  for lg in runs/generic-rep1-31b.log runs/generic-rep2-31b.log runs/generic-dev20-31b.log runs/official-generic-v1-31b.log; do
    [ -f $lg ] && grep -h "Traceback\|Error:" $lg 2>/dev/null | grep -v "W1118\|Warning" | tail -2 | while read -r l; do emit "ERROR $(basename $lg): ${l:0:160}"; done
  done
  sleep 30
done
