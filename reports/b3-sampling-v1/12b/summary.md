# b3-sampling-v1 — 12B

Trạng thái: `complete`

| prompt | seed | guard | generations | guard_reasked | pattern | perf | tests | public_diff | public_pass | accepted_audit | selected |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ABC | 1 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^<>\r\n]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | False | False | False |  |
| ABC | 2 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^> <]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | False | False | False | False |  |
| ABC | 3 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^> <]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | False | False | False | False |  |
| ABC | 4 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\[<]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | True | True | True | True |
| ABC | 5 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\[\n\r]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | False | True | False | False | False |  |
| ABC | 6 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^> <]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | False | False | False | False |  |
| AG | 1 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | False | False | False |  |
| AG | 2 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | False | False | False |  |
| AG | 3 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | False | False | False |  |
| AG | 4 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | True | True | False | False | False |  |
| AG | 5 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*[^>]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | False | True | True | False | False |  |
| AG | 6 | ok | 1 | False | _baseurl_re = re.compile(
    r"<base\s[^>\s]*\w*\s*[^>]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE
) | False | True | True | False | False |  |

Chọn theo public: `{"ABC": {"selected_seed": 4, "selected_accepted": true}, "AG": {"selected_seed": null, "selected_accepted": null}}`
