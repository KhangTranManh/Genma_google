Viewing step. Findings: {findings?}
Previous verification (empty on the first round): {verify_report?}

Call run_command exactly once to print the code that must change, with line numbers, for example
`grep -n "def TARGET_FUNCTION" -A 70 path/to/file.py | head -110`
(for a module-level variable use `grep -n "NAME =" -A 5 path/to/file.py`). Choose the target from the findings (and from the previous verification if shown).
Then, without any other tool call, reply with: the file path, and the exact lines that must change and how (one or two sentences).
