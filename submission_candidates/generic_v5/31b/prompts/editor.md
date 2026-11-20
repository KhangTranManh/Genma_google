Repair step. Findings: {findings?}
Previous verification (empty on the first round): {verify_report?}

View only the target function(s) with run_command (at most 2 calls), e.g. `grep -n "def NAME" -A 60 path/to/file.py | head -90` or `sed -n 'A,Bp' path/to/file.py`.

Then make the fix with edit_file using the SHORTEST old_string that is unique in the file and contains the characters you change: usually a fragment of a single line, not whole statements. Avoid quote characters and backslashes in old_string/new_string whenever a shorter fragment without them is unique (they can be altered in transit). Example: to change `[^>]*href` inside a long regex, use old_string `[^>]*href` and new_string `[^<>]*href`. Copy the fragment exactly from the viewed source, without the line-number prefixes that grep -n adds.
If edit_file reports "old_string not found", do NOT resend the same text: view the line again and use a shorter fragment. Several small edit_file calls are fine.

Fix the root cause in general with the smallest change; keep public signatures and unrelated behavior; do not special-case the reproduction input; never edit _repro_check.py or tests. If a previous verification is shown, change what it says is still wrong instead of repeating the same edit.
After the edit succeeds, reply with one line describing the change and stop.
