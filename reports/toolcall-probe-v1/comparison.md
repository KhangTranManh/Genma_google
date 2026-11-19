# Same-generation tool-call/parser probe

Eight short single-call requests; not long conversations, streaming, real-repo solving or an error-rate estimate.

Captured 8/8. Tools executed: 0.

| Model | Case | Label | Raw expected | API expected | Replay = API |
|---|---|---|---|---|---|
| 12b | read_range | correct | True | True | True |
| 12b | write_quotes_newlines | correct | True | True | True |
| 12b | edit_exact_line | raw_output_defect | False | False | True |
| 12b | run_test_command | correct | True | True | True |
| 31b | read_range | correct | True | True | True |
| 31b | write_quotes_newlines | correct | True | True | True |
| 31b | edit_exact_line | correct | True | True | True |
| 31b | run_test_command | correct | True | True | True |

## Diễn giải

- 8/8 capture có native arguments, API arguments và engine replay khớp nhau. Chưa tái hiện mất/ghép field do parser trong bộ ca nhỏ này.
- 12B/edit_exact_line: output gốc là read_file(src/example.py), trong khi yêu cầu edit_file. Đây là lệch lựa chọn tool so với yêu cầu, không phải native syntax hỏng hay field bị parser làm mất. Có thể liên quan thói quen đọc trước sửa; phép thử chưa xác định cơ chế nội tại.
- Chưa kiểm tra ADK/LiteLLM response adapter, streaming, chuỗi hội thoại dài hoặc run_skill_script với arguments lồng nhau. Không kết luận parser hoàn toàn không lỗi hoặc quy mọi thất bại repo cho model.
- Bước tiếp theo nên tái hiện một trường hợp từng lỗi bằng context/schema phức tạp hơn, vẫn thu raw và parsed cùng generation; không sửa parser hoặc weights chỉ dựa vào 8 mẫu này.
