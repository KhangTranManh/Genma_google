# Inspection checkpoint

Keep this short in the conversation; do not create repository note files:

- Requirement: which behavior must change?
- Evidence: path:symbol or bounded line range, and what it proves.
- Hypothesis: cause consistent with that evidence; mark unresolved assumptions.
- Next action: reproduce, edit, test, or resolve one named missing fact.
- Verification: last command and result on the current code, if any.

Inspection is useful when it changes the hypothesis or enables a concrete next
action. Reading a second caller is justified if behavior crosses modules. Reading
the same unchanged code without a new question is not useful progress.

After a test failure, use the failure to narrow the next inspection. Once the
requested behavior and relevant regressions pass, review the diff and submit.
