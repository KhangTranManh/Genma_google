You are the final step. Previous verification: {verify_report?}

1. run_command `rm -rf .harness && git status --short` (helper files must not be part of the patch).
2. If `git status --short` shows no change to repository source files, say "NO CHANGE" and still call submit_patch.
3. Call submit_patch exactly once.
Finish with the submit result.
