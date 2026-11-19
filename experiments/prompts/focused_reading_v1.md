
Focused repository reading protocol:
- Before each inspection, decide the concrete question it should answer: where the
  behavior lives, what the caller expects, or how an existing test exercises it.
- Locate symbols first with a bounded search. Prefer rg when installed; otherwise
  use git grep -n. Find likely paths with git ls-files and a narrow path pattern.
  Avoid recursive dumps of the repository or entire large test files.
- Read a bounded window around the relevant definition, usually 60-120 lines and
  never more than the tool's advertised limit. Read callers or adjacent helpers only
  when they resolve a specific uncertainty. A bug may legitimately span many files.
- Pass tool arguments as separate JSON fields. For example:
  read_file: {"filepath":"src/example/module.py","start_line":80,"end_line":150}
  filepath contains only the path. Do not append commas, backticks, option names,
  start_line, or end_line to the filepath string. Line bounds are integers.
- If a tool rejects arguments, correct the structure once. If the path is absent,
  locate the real path with a targeted search. Do not repeat an unchanged failed call.
- Treat four inspection calls as a checkpoint, not a hard cap. Briefly summarize
  the suspected cause, relevant path/symbol and next check. Then reproduce, edit or
  run a focused test. Continue inspecting only if you can state what remains unknown
  and how the next read resolves it. Do not fabricate a fix just to meet a read quota.
- Do not reread an unchanged region unless a new error, caller or changed hypothesis
  makes that reread necessary. If a result is truncated, request the missing range
  rather than repeating the same full-file request.
- Preserve a short working summary in the conversation: requirement, evidence,
  suspected cause, edited files, latest test result and next action. Do not create
  repository files merely to hold agent notes.
- Verify the requested behavior and relevant existing tests. If tests fail, inspect
  that failure and change the implementation; repeated successful checks are not
  progress. Review the patch, then call submit_patch within the remaining budget.
