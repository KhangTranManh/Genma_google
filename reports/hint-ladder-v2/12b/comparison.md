# Hint ladder v2 — 12B

Trạng thái: `complete` · Preflight bộ chấm dùng được: `True`

Trần 1536 token. Các nhánh không có seed dùng temperature 0; nhánh seed dùng 0.6. Vòng phản hồi (chỉ 12B) sửa trên code tích lũy, chỉ thấy kết quả công khai. `api_accepted` = qua kiểm tra hiệu năng công khai, 67 test chức năng, bộ chấm độc lập và kiểm tra thuộc tính dài. Kết quả chỉ của model này; không gộp với model khác.

| arm | output_tokens | finish_reason | capture | raw_equals_api | call_valid | literal_match | public_perf | public_median_s | functional | independent | long_attr | api_accepted | api_category | raw_category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A+B+C lượt đầu | 140 | tool_calls | captured | True | True | True | True | 0.0002869990130420774 | False | False | False | False | functional_fail | functional_fail |
| A+B+C phản hồi vòng 1 | 141 | tool_calls | captured | True | True | True | None | None | None | None | None | False | tool_error | tool_error |
| A+B+C phản hồi vòng 2 | 141 | tool_calls | captured | True | True | True | None | None | None | None | None | False | tool_error | tool_error |
