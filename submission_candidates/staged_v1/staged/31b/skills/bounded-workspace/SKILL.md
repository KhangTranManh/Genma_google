---
name: bounded-workspace
description: Bounded literal search, small file reads, fixed pytest and diff-stat checks inside the task sandbox; prevents unlimited direct inspection through this interface.
---

Use run_skill_script with skill_name="bounded-workspace", file_path="scripts/workspace_ops.py"
and args as a list of strings. Examples:

- Search: ["search", "--path", "src", "--needle", "def function_name"]
- Read: ["read", "--path", "src/module.py", "--start", "40", "--end", "100"]
- Test: ["test", "--path", "tests/test_module.py"]
- Review summary: ["review"]
- Budget: ["status"]

Use actual repository paths. All operations stay inside /workspace. The interface
permits 8 successful inspection requests across search/read, at most 2 repeats of an
unchanged request, 4 pytest invocations and 2 diff-stat reviews per sandbox. File
reads return at most 80 lines and 2400 characters. Search is literal, not a shell
command. Test runs the fixed pytest command with a 45-second timeout.

A denied request is not a reason to retry it. Edit based on the evidence, run a
focused test, or finish your current stage with a concise blocker. Do not bypass
the inspection limit by creating test code whose purpose is to print source files.
Never weaken tests, modify git history, or edit the skill's state files.

The script enforces limits on its own interface; it does not limit the number of
LLM calls in an ADK stage or guarantee automatic handoff. Test code still runs as
repository code inside the sandbox. This is an experiment in orchestration, not
an adversarial security boundary.
