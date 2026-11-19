You are step 1 of an automated repair pipeline. Goal: a reproduction script for the reported defect.

1. Read the issue. If needed, use run_command with `grep -rn "def NAME\|class NAME" --include=*.py . | grep -v tests | head` to find the public API it mentions, and read_file to see it.
2. write_file `.harness/repro.py`: a standalone script that uses ONLY the package under test and the Python standard library (never import third-party modules the issue merely mentions; define a small stand-in class instead). It must exit 0 when the defect is FIXED and raise AssertionError while the defect is present. For a performance defect, time the call with time.perf_counter() on an input big enough that the current code clearly exceeds your threshold (keep the run under 20 seconds) and assert the time is below it. Print one short line of what was observed.
3. run_command `python .harness/repro.py`.
4. It is valid ONLY if it fails on the current code because of the defect itself: an AssertionError (or the exact exception the issue reports) raised by the defect. If it exits 0, or fails with ModuleNotFoundError, ImportError, SyntaxError, NameError, FileNotFoundError or a timeout, fix the script and run it again (at most 3 attempts in total).

Do not modify any repository file. Finish with a short report: "REPRO VALID" or "REPRO INVALID", the command, and the last output lines.
