You are step 2 of an automated repair pipeline. Goal: find the code that must change, using runtime evidence.

Reproduction report from step 1:
{repro_report?}

1. If the reproduction is valid, collect evidence with ONE of these commands:
   - performance defect: `timeout 50 python -m cProfile -s tottime .harness/repro.py 2>&1 | grep -v -e site-packages -e "{built-in" -e "<frozen" | head -45`
   - exception defect: the traceback frames inside the repository from `python .harness/repro.py`.
   The repository functions with the most own time (tottime) or deepest repository frames are the strongest candidates.
2. Confirm with read_file on the candidate functions. Use grep (`grep -rn ... --include=*.py`) only to locate definitions.
3. Identifiers in the issue text can point to wrappers; prefer the code the evidence shows doing the work.

Do not modify files. Finish with a short list of at most 3 targets as `path::function_or_class` with one line of reasoning each, most likely first.
