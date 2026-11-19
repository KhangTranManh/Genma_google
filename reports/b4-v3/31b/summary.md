# B4 v3 — 31B

Trạng thái: `complete`

| task | sample | round | regions | guards | perf per function | tests | diff | public | accepted (audit) |
|---|---|---|---|---|---|---|---|---|---|
| w3lib_266 | t0 | 0 | [0] | ['ok'] | {'get_meta_refresh': True} | True | True | True | True |
| w3lib_268 | t0 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | t0 | 1 | [0, 1] | ['ok', 'noop'] | {'replace_tags': True, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s17 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s17 | 1 | [0, 1] | ['ok', 'noop'] | {'replace_tags': True, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s29 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s29 | 1 | [0, 1] | ['ok', 'ok'] | {'replace_tags': True, 'remove_tags': True} | True | False | False | False |
| w3lib_268 | s43 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': True} | True | False | False | False |
| w3lib_268 | s43 | 1 | [0, 1] | ['ok', 'ok'] | {'replace_tags': True, 'remove_tags': True} | True | False | False | False |
| w3lib_268 | s5 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s5 | 1 | [0, 1] | ['ok', 'ok'] | {'replace_tags': True, 'remove_tags': True} | False | False | False | False |
| w3lib_268 | s11 | 0 | [0, 1] | ['ok', 'ok'] | {'replace_tags': False, 'remove_tags': False} | True | True | False | False |
| w3lib_268 | s11 | 1 | [0, 1] | ['ok', 'ok'] | {'replace_tags': True, 'remove_tags': True} | False | False | False | False |
| w3lib_271 | t0 | 0 | [0] | ['ok'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | t0 | 1 | [0] | ['ok'] |  |  |  |  |  |
| w3lib_271 | s17 | 0 | [0] | ['ok'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s17 | 1 | [0] | ['not_found'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s29 | 0 | [0] | ['noop'] |  |  |  |  |  |
| w3lib_271 | s29 | 1 | [0] | ['ok'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s43 | 0 | [0] | ['ok'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s43 | 1 | [0] | ['not_found'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s5 | 0 | [0] | ['ok'] | {'remove_tags_with_content': True} | True | False | False | False |
| w3lib_271 | s5 | 1 | [0] | ['ok'] |  |  |  |  |  |
| w3lib_271 | s11 | 0 | [0] | ['ok'] | {'remove_tags_with_content': False} | True | True | False | False |
| w3lib_271 | s11 | 1 | [0] | ['not_found'] | {'remove_tags_with_content': False} | True | True | False | False |

## Chọn theo public

- w3lib_266: {'selected': 't0', 'selected_accepted': True, 'samples_used': 1}
- w3lib_268: {'selected': None, 'selected_accepted': None, 'samples_used': 6}
- w3lib_271: {'selected': None, 'selected_accepted': None, 'samples_used': 6}
