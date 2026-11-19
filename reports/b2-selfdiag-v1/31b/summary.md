# b2-selfdiag-v1 — 31B

Trạng thái: `complete`

| arm | traj | diagnosis_parsed | diagnosis_truncated | final_public_pass | final_accepted | accepted_round0 |
|---|---|---|---|---|---|---|
| selfdiag_G | t0 | True | False | False | False | False |
| selfdiag_G | s17 | True | False | False | False | False |
| selfdiag_G | s29 | True | False | True | True | True |
| selfdiag_G | s43 | True | False | False | False | False |
| hostA_G | t0 |  |  | False | False | False |
| hostA_G | s17 |  |  | False | False | False |
| hostA_G | s29 |  |  | False | False | False |
| hostA_G | s43 |  |  | False | False | False |

## Các vòng

- selfdiag_G/t0 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- selfdiag_G/t0 r1: guard=invalid gen=1 public=False accepted=False ``
- selfdiag_G/s17 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- selfdiag_G/s17 r1: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?\bhref\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- selfdiag_G/s29 r0: guard=ok gen=1 public=True accepted=True `r"<base\s[^<>]*href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- selfdiag_G/s43 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- selfdiag_G/s43 r1: guard=invalid gen=1 public=False accepted=False ``
- hostA_G/t0 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^<]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/t0 r1: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s17 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^<]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s17 r1: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s29 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^<]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s29 r1: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s43 r0: guard=ok gen=1 public=False accepted=False `r"<base\s[^<]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
- hostA_G/s43 r1: guard=ok gen=1 public=False accepted=False `r"<base\s[^>]*?href\s*=\s*[\"\']\s*([^\"\'\s]+)\s*[\"\']", re.IGNORECASE`
