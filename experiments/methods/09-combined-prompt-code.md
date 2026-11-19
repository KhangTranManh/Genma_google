# Kết hợp code harness mới và prompt mới

Trên 12B và 31B, so sánh cặp mới, giữ tách riêng đợt ablation trước:

| Experiment | Code | Prompt | History |
|---|---|---|---|
| combined_control_v1 | ProgressAgent revision 2, detect_only | tool_recovery_v1 | 12.000 ký tự |
| combined_prompt_v1 | Cùng revision 2, detect_only | completion_contract_v1 | 12.000 ký tự |

4 lượt smoke: mỗi cấu hình chạy 12B rồi 31B. Tất cả model tự submit, không harness
nộp hộ. Giữ checkpoint, temperature=0, thinking=false, vLLM TP=2,
8192 model context, 2048 max output tokens, 900 giây / 48 lượt / 96 tool requests.
Chỉ thay prompt; source code và runtime giữ nguyên, đóng băng trước khi bắt đầu.

Tiêu chí chính: nguồn submit=model và test độc lập pass toàn bộ. Nếu cả hai pass,
so thời gian, tokens, turns và tool calls. Nếu candidate làm mất pass thì chưa chọn.
Patch thu hồi chỉ chẩn đoán; không tính thành tự hoàn tất. Giữ lịch sử các đợt cũ.

Mỗi ô có một mẫu trên URLKit; đây là sàng lọc tương tác code+prompt. Sau đó cần
chạy lặp và bộ nhiều issue/repo trước khi chọn cấu hình cuối hoặc kết luận tổng quát.
Chưa triển khai đánh giá nhiều repo trong đợt smoke này.

Report: reports/two-model-combined.{md,json,csv} và reports/study-report.html.
Study trigger tự chuyển nhánh, lưu bằng chứng và dừng ở complete/needs_review.
