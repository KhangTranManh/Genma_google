Repair step. Findings: {findings?}
Previous verification (empty on the first round): {verify_report?}

View only the target function(s) with run_command (at most 2 calls), e.g. `grep -n "def NAME" -A 60 path/to/file.py | head -90` or `sed -n 'A,Bp' path/to/file.py`. Then make the fix with edit_file, copying old_string exactly from the viewed source WITHOUT the line-number prefixes that grep -n adds. Fix the root cause in general with the smallest change; keep public signatures and unrelated behavior; do not special-case the reproduction input; never edit _repro_check.py or tests. If a previous verification is shown, change what it says is still wrong instead of repeating the same edit.
After the edit, reply with one line describing the change and stop.
