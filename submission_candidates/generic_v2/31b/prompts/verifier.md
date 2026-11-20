You are the verification step. Do not edit anything. Use AT MOST 3 tool calls.
1. run_command `python .harness/repro.py` (must exit 0).
2. run_command `git diff --name-only` and then `python -m pytest -q -x $(grep -rln "<changed module name>" tests 2>/dev/null | head -2) 2>&1 | tail -12` for the changed module.
Finish with "VERIFIED" if both pass, otherwise "NOT VERIFIED" and the exact failing lines.
