You are step 3 of an automated repair pipeline. Goal: behavior checks that a correct fix must satisfy.

Reproduction report: {repro_report?}
Targets: {targets?}

write_file `.harness/checks.py`, using only the package under test and the standard library:
- 3 to 5 functions `fixed_<name>()`: other inputs, code paths or sibling functions affected by the SAME defect beyond the single example in the issue. Each raises AssertionError while the defect is present.
- 3 to 5 functions `preserve_<name>()`: normal documented behavior near the target code that must stay exactly the same, including error cases that must still raise.
- At the end exactly this runner:
```python
if __name__ == "__main__":
    import sys, traceback
    bad = []
    for n, f in sorted(globals().items()):
        if callable(f) and n.startswith(("fixed_", "preserve_")):
            try:
                f(); print("PASS", n)
            except Exception as e:
                print("FAIL", n, type(e).__name__, str(e)[:150]); bad.append(n)
```
Then run_command `timeout 60 python .harness/checks.py`. On the CURRENT code every preserve_* must PASS and every fixed_* must FAIL with an AssertionError. Rewrite or delete checks that do not behave like that (one rewrite round). Do not modify repository files.
Finish with: the final list of kept checks and their current PASS/FAIL status.
