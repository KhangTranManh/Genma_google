# Định nghĩa giai đoạn tiếp theo: 12B và 31B

Trạng thái: đã định nghĩa, chưa chạy đợt mới. E4B dừng ở phạm vi nghiên cứu tiếp theo;
checkpoint và kết quả cũ được giữ. Không sửa lại thiết kế hay kết quả A/B/C đã hoàn tất.

## Bằng chứng và mục tiêu riêng

| Model | Bằng chứng trên URLKit | Mục tiêu tiếp |
|---|---|---|
| 12B | A/B patch thu hồi 6/6 nhưng không submit; C harness nộp 6/6 trong 69.438s | Giữ chất lượng patch, tự gọi submit_patch sau review và verification |
| 31B | A hết 48 lượt; B tự submit 6/6 trong 18 lượt / 219.025s | Giữ khả năng tự hoàn tất, giảm thao tác thừa và kiểm chứng trên nhiều issue |

## Thử nghiệm 12B: chỉ đổi prompt kết thúc

- Đối chứng: `progress_guard_v1` trên 12B; cần chạy lại cùng phiên bản workflow hiện tại
  khi đánh giá cặp, không dùng số cũ làm baseline duy nhất.
- Candidate: `focus_12b_completion_v1`, cấu hình `focus_12b.toml`.
- Giữ ProgressAgent ở detect_only. Thêm checklist hoàn tất vào bản prompt mới;
  không bật harness tự nộp, không đổi schema tool/compact context/ngân sách trong đợt này.
- Điều kiện từng lượt: source và regression test hợp lệ, kiểm tra public trên đúng
  code version, model tự submit, test độc lập sau kết thúc pass toàn bộ.
- Prompt phải xử lý cả submit bị yêu cầu review: đọc diff trả về rồi submit lần nữa.
- Nếu vẫn stalled dù patch đúng: dùng trajectory để xác định context bị quên hay
  tool bị hạn chế; thử thay đổi runtime ở một experiment mới, không gộp vào prompt-only.

## Thử nghiệm 31B: tái kiểm chứng cấu hình B trước tối ưu

- Candidate tham chiếu: `focus_31b_reliability_v1`, cấu hình `focus_31b.toml`;
  giữ prompt recovery và detect_only đã thành công. Đây là tái kiểm chứng,
  chưa phải một cải tiến đã được chứng minh.
- Giữ repeat_limit=2, stagnation_limit=16, fallback edit và trạng thái phiên bản.
- Điều kiện từng lượt: model tự submit; test độc lập pass; không lặp tới hết lượt.
- Chỉ sau khi đạt chất lượng mới thử tiết kiệm token: prompt ngắn hơn HOẶC compact
  context khác, mỗi lần một yếu tố và một experiment ID riêng.
- Không tăng 48 lượt/900 giây để che loop, không mặc định quy lỗi cho model chậm.

## Điều kiện chung để chấp nhận cải tiến

1. Smoke URLKit: 3 lần mỗi cấu hình/model; ghi rõ mức biến thiên nếu kết quả khác nhau.
2. Trước khi đánh giá tổng quát, chuẩn bị bộ ít nhất 10 issue chạy được từ ít nhất
   3 repo, đóng băng commit, dependency, test public/độc lập và giới hạn tài nguyên.
   Chưa có bộ này; không tính URLKit thành 10 issue hoặc dùng test độc lập làm prompt.
3. Tách tập phát triển và tập xác nhận; chốt candidate trước khi xem kết quả xác nhận.
4. Chạy cặp baseline/candidate trên cùng issue, seed (nếu runtime hỗ trợ), ngân sách
   và phần cứng; 3 lần/issue là mục tiêu ban đầu, không phải bảo đảm ý nghĩa thống kê.
5. Tiêu chí chính: autonomous success = nguồn nộp model VÀ pass test độc lập.
   Không chấp nhận candidate chỉ vì recovered patch pass hoặc harness nộp hộ.
6. Chấp nhận khi số autonomous success tăng và không mất issue đã pass ổn định;
   báo cáo cặp thắng/thua/hòa, độ biến thiên và các regression. Nếu chưa rõ, giữ baseline.
7. Sau khi giữ được chất lượng, chọn candidate có thời gian/token trung vị thấp hơn;
   báo cáo thêm p95 khi có đủ mẫu. Không xếp hạng từ một lần chạy hoặc chỉ tokens/s.
8. Đối chiếu official agent.yaml/tool schema/harness trước khi dùng kết quả local
   cho submission. ProgressAgent local và chế độ C chưa được xác nhận dùng được trong đề.

## Ngân sách và phạm vi

Giữ 900 giây, 48 lượt, 96 yêu cầu tool, cùng vLLM TP=2, checkpoint và thinking=false.
Không fine-tune/tăng context/tăng sampling đồng thời với sửa prompt. LoRA chỉ cân nhắc
sau khi có nhiều trajectory thất bại nhất quán và tập xác nhận riêng.

Cấu hình focus chỉ chứa một model trong automation.model_order. Chưa thêm vào study
đã hoàn tất và chưa bật trigger đợt mới để tránh báo cáo nhầm definition thành kết quả.
