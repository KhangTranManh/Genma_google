# Hint ladder v2 — 31B

Trạng thái: `complete` · Preflight bộ chấm dùng được: `True`

Trần 1536 token. Các nhánh không có seed dùng temperature 0; nhánh seed dùng 0.6. Vòng phản hồi (chỉ 12B) sửa trên code tích lũy, chỉ thấy kết quả công khai. `api_accepted` = qua kiểm tra hiệu năng công khai, 67 test chức năng, bộ chấm độc lập và kiểm tra thuộc tính dài. Kết quả chỉ của model này; không gộp với model khác.

| arm | output_tokens | finish_reason | capture | raw_equals_api | call_valid | literal_match | public_perf | public_median_s | functional | independent | long_attr | api_accepted | api_category | raw_category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B (nguyên tắc riêng, không A) | 146 | tool_calls | captured | True | True | True | False | 1.1399722350179218 | True | False | True | False | public_performance_fail | public_performance_fail |
| G (checklist regex chung) | 146 | tool_calls | captured | True | True | True | False | 1.1739736949966755 | True | False | True | False | public_performance_fail | public_performance_fail |
| A+G | 146 | tool_calls | captured | True | True | True | True | 0.00026846802211366594 | True | True | True | True | accepted | accepted |
| AB seed 17 | 146 | tool_calls | captured | True | True | True | True | 0.00029716198332607746 | True | True | True | True | accepted | accepted |
| AB seed 29 | 146 | tool_calls | captured | True | True | True | True | 0.0002935270022135228 | False | False | False | False | functional_fail | functional_fail |
| AB seed 43 | 146 | tool_calls | captured | True | True | True | True | 0.00029647399787791073 | True | True | True | True | accepted | accepted |
| AG seed 17 | 146 | tool_calls | captured | True | True | True | True | 0.00028136299806647 | True | True | True | True | accepted | accepted |
| AG seed 29 | 146 | tool_calls | captured | True | True | True | True | 0.00028125799144618213 | True | True | True | True | accepted | accepted |
| AG seed 43 | 145 | tool_calls | captured | True | True | True | True | 0.00027398898964747787 | True | True | True | True | accepted | accepted |
