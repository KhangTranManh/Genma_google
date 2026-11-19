You are the verification step of an automated pipeline. Do not edit anything.

Run, in this order, each with run_command:
1. `python .harness/repro.py` (must exit 0)
2. `timeout 60 python .harness/checks.py` (if the file exists; every listed check must print PASS)
3. the existing tests of the changed module: find them with `git diff --name-only` and `grep -rln "<module name>" tests | head -3`, then `python -m pytest -q -x <those files> 2>&1 | tail -15`
Finish with "VERIFIED" if all pass, otherwise "NOT VERIFIED" followed by the exact failing items and error lines (they are passed to the next repair round).
