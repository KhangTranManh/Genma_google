# Hint ladder v1 — 12B

Trạng thái: `complete` · Preflight bộ chấm dùng được: `True`

Một lần sinh mỗi mức, temperature 0, trần 1536 token, mỗi mức bắt đầu từ code gốc. `api_accepted` = qua kiểm tra hiệu năng công khai, 67 test chức năng, bộ chấm độc lập và kiểm tra thuộc tính dài. Kết quả chỉ của model này; không gộp với model khác.

| arm | output_tokens | finish_reason | capture | raw_equals_api | call_valid | literal_match | public_perf | public_median_s | functional | independent | long_attr | api_accepted | api_category | raw_category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Đối chứng | 141 | tool_calls | captured | True | True | True | False | 1.1267207610071637 | True | False | True | False | public_performance_fail | public_performance_fail |
| A (cơ chế) | 146 | tool_calls | captured | True | True | True | False | 1.1261800929787569 | False | False | True | False | public_performance_fail | public_performance_fail |
| A+B (+nguyên tắc sửa) | 144 | tool_calls | captured | True | True | True | False | None | True | False | True | False | public_performance_fail | public_performance_fail |
| A+B+C (+ví dụ cùng loại) | 140 | tool_calls | captured | True | True | True | True | 0.0002959780103992671 | False | False | False | False | functional_fail | functional_fail |
