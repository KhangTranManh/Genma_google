# Hint ladder v1 — 31B

Trạng thái: `complete` · Preflight bộ chấm dùng được: `True`

Một lần sinh mỗi mức, temperature 0, trần 1536 token, mỗi mức bắt đầu từ code gốc. `api_accepted` = qua kiểm tra hiệu năng công khai, 67 test chức năng, bộ chấm độc lập và kiểm tra thuộc tính dài. Kết quả chỉ của model này; không gộp với model khác.

| arm | output_tokens | finish_reason | capture | raw_equals_api | call_valid | literal_match | public_perf | public_median_s | functional | independent | long_attr | api_accepted | api_category | raw_category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Đối chứng | 146 | tool_calls | captured | True | True | True | False | 1.1304106249881443 | True | False | True | False | public_performance_fail | public_performance_fail |
| A (cơ chế) | 146 | tool_calls | captured | True | True | True | False | 1.1359041529940441 | True | False | True | False | public_performance_fail | public_performance_fail |
| A+B (+nguyên tắc sửa) | 146 | tool_calls | captured | True | True | True | True | 0.00029963499400764704 | True | True | True | True | accepted | accepted |
| A+B+C (+ví dụ cùng loại) | 145 | tool_calls | captured | True | True | True | True | 0.0002879890089388937 | True | True | True | True | accepted | accepted |
