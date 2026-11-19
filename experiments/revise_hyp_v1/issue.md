w3lib.html.get_base_url() can be slow due to quadratic regex complexity

Calling get_base_url("<base " * 30000) takes several seconds on malformed HTML. Repair this performance problem while preserving extraction of base URLs from normal HTML and the existing behavior of get_base_url().

This is a development diagnostic with a solution-redacted issue, not the verbatim upstream issue.
