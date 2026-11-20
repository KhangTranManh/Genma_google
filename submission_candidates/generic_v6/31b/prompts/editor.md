Editing step. You can only call edit_file.
Findings: {findings?}
Code view and plan: {code_view?}
Previous verification (empty on the first round): {verify_report?}

Make the fix with edit_file now, using the SHORTEST old_string that is unique in the file and contains the characters you change (usually part of one line). Copy it exactly from the code view WITHOUT the "123:" or "123-" line-number prefixes. Avoid quote characters and backslashes in old_string/new_string when a shorter fragment without them is unique. If edit_file reports "old_string not found", use a shorter fragment; at most 4 edit_file calls in total.
Fix the root cause in general with the smallest change; keep public signatures and unrelated behavior; do not special-case the reproduction input; never edit _repro_check.py or tests.
Then reply with one line describing the change.
