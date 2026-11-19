# Bounded file reads and valid arguments

A read_file call has separate JSON fields:

{"filepath":"src/example/module.py","start_line":80,"end_line":150}

Replace the example with the path and line range found in this repository.
Use integer line numbers. filepath is only a path: do not put `,start_line:80`,
backticks, shell syntax or a serialized JSON object inside it. Displayed line
numbers are not part of file contents for edit_file replacements.

Locate a definition before selecting its window. A targeted command example is:

{"command":"git grep -n 'def relevant_function' -- src tests"}

Check actual repository paths first. `rg` is optional; don't install it in an
offline task. If output is truncated, narrow the symbol/path or request only the
missing lines. Do not rerun the identical truncated request.

When a file is absent, use git ls-files with a narrow pattern and use the returned
path. When an exact edit fails, reread the relevant current lines, then use a
short unique replacement. Never manually double-escape JSON arguments.
