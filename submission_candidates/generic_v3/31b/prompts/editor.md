Repair step. Findings: {findings?}
Previous verification (empty on the first round): {verify_report?}

read_file only the target function(s) (use start_line/end_line; at most 3 reads), then make the fix with edit_file, copying old_string exactly from what read_file showed. Fix the root cause in general with the smallest change; keep public signatures and unrelated behavior; do not special-case the reproduction input; never edit _repro_check.py or tests. If a previous verification is shown, change what it says is still wrong instead of repeating the same edit.
After the edit, reply with one line describing the change and stop.
