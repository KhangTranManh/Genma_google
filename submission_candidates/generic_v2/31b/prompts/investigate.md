You are step 1 of an automated repair pipeline with a hard time budget. Use AT MOST 8 tool calls in this step.

1. FIRST run_command: `mkdir -p .harness && echo ".harness/" >> .git/info/exclude`
2. write_file `.harness/repro.py`: a standalone script using ONLY the package under test and the standard library (define a small stand-in class instead of importing third-party modules the issue mentions). It exits 0 when the defect is FIXED and lets an AssertionError (or the defect's own exception raised inside the package) propagate while the defect is present. Do not wrap calls in try/except. For performance defects, time the call with time.perf_counter() on an input large enough that the current code clearly exceeds your threshold (run time under 20 s). Check real signatures in the source before calling an API.
3. run_command `python .harness/repro.py`. If it fails because of the script itself (ImportError, wrong arguments/TypeError raised in the script, NameError, SyntaxError) or exits 0, fix it once and rerun.
4. Evidence: run_command `timeout 50 python -m cProfile -s cumtime .harness/repro.py 2>&1 | grep -v -e site-packages -e "{built-in" -e "<frozen" -e "<module>" | head -40`. Repository functions in this list (for wrong results) or with the largest tottime (for slowness), and repository frames in a traceback, show where the defect is.
5. read_file the one or two most likely functions (use start_line/end_line to read only those).

Do not modify repository files. Finish with: REPRO VALID/INVALID, the repro command, and at most 2 targets `path::function` with one line of reasoning each.
