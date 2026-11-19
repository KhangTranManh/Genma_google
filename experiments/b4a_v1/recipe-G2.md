Regex backtracking repair recipe for patterns that scan markup tags (apply to every supplied excerpt whose function is reported slow):
1. Locate each unbounded span inside a tag pattern: `.*?`, `.*`, `[^>]*`, `[^>]*?`, `[^X]+` and similar.
2. Replace that span with a character class that excludes BOTH the tag's closing delimiter and the opening delimiter of a new tag, e.g. `[^>]*` -> `[^<>]*` and `.*?>` -> `[^<>]*>`. Excluding only one of them is not enough: `[^<]*` crosses `>` and changes which text is treated as the tag; `[^>]*` still rescans from every `<`.
3. Do NOT switch to a lazy quantifier (`*?`, `+?`): it does not remove the rescanning on failing inputs.
4. Keep everything else unchanged: tag-name groups, alternations, flags, backreferences, surrounding code. If a tag-name group such as `([^ >/]+)` can also run over `<`, add `<` to its excluded set (`[^ <>/]+`) instead of rewriting the group.
5. If a pattern also spans content between an opening and a closing tag (e.g. `>.*?</tag>`), repair the attribute span of the opening tag first; content may legitimately contain `>`.
6. If no regex span is responsible (e.g. a loop rescans from the start), make each step continue from where the previous one ended instead of rescanning.
