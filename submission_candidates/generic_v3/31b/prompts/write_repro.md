Step 1 of an automated repair pipeline. Your only job: write ONE reproduction script, then stop.

Optionally read_file the code the issue names (at most 2 reads, use start_line/end_line). Then call write_file exactly once with
filepath: _repro_check.py
content: a standalone script using ONLY the package under test and the standard library (define a small stand-in class instead of importing third-party modules the issue mentions; check real signatures in the source). It must exit 0 when the defect is FIXED and let an AssertionError propagate while the defect is present (no try/except, no sys.exit). For performance defects, time the call with time.perf_counter() on an input large enough that the current code clearly exceeds your threshold, keeping the run under 20 seconds.

After the write_file call, reply with one line saying what the script checks. Do not call any other tool.
