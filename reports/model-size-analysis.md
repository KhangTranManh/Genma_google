# Phân tích kích thước model và lỗi workflow

## Phạm vi kết luận

Đã có 9/9 lượt dừng. Đã đủ chín lượt để tổng kết đợt thử. Chỉ một issue và một lần chạy mỗi cấu hình. Chưa xác định quan hệ nhân quả giữa số tham số và tỷ lệ lỗi, chưa đủ kết luận model lớn kém hơn nói chung.

## Vì sao nhiều tham số chưa đảm bảo hoàn thành agent

Kết quả đo là cả chuỗi đọc repo → sửa code → kiểm tra → nộp patch. Cần tách khả năng sửa đúng khỏi khả năng gọi tool và kết thúc đúng quy trình. Không submit, patch sai và hết thời gian là những kiểu thất bại khác nhau.

## 31B — bằng chứng đã quan sát

progress_baseline_v1: incomplete, dừng=turn_limit, nguồn nộp=không có, request trùng nguyên văn=39, thử submit=0 (run 20261116T064438Z-a5dae13e). progress_guard_v1: local_pass, dừng=submitted, nguồn nộp=model, request trùng nguyên văn=5, thử submit=2 (run 20261116T070957Z-325fe24c). progress_finish_v1: local_pass, dừng=harness_submitted, nguồn nộp=harness, request trùng nguyên văn=3, thử submit=0 (run 20261116T073405Z-5be811c3).

## 12B — bằng chứng đã quan sát

progress_baseline_v1: incomplete, dừng=turn_limit, nguồn nộp=không có, request trùng nguyên văn=35, thử submit=0; patch thu hồi pass nhưng không tính thành công (run 20261116T065237Z-2f2f1f79). progress_guard_v1: incomplete, dừng=stalled, nguồn nộp=không có, request trùng nguyên văn=9, thử submit=0; patch thu hồi pass nhưng không tính thành công (run 20261116T071557Z-8c31c62e). progress_finish_v1: local_pass, dừng=harness_submitted, nguồn nộp=harness, request trùng nguyên văn=2, thử submit=0 (run 20261116T073927Z-cd0ec631).

## E4B — bằng chứng đã quan sát

progress_baseline_v1: incomplete, dừng=turn_limit, nguồn nộp=không có, request trùng nguyên văn=24, thử submit=2 (run 20261116T065837Z-c3cb7105). progress_guard_v1: incomplete, dừng=turn_limit, nguồn nộp=không có, request trùng nguyên văn=20, thử submit=2 (run 20261116T071942Z-c13011dd). progress_finish_v1: incomplete, dừng=turn_limit, nguồn nộp=không có, request trùng nguyên văn=21, thử submit=0 (run 20261116T074230Z-722f1299).

## 31B: nguyên nhân dừng đã xác nhận

Lượt 31B dừng vì turn_limit đã dùng hết ngân sách lượt. Với lượt đó, không thể quy nguyên nhân dừng trực tiếp cho tốc độ token hoặc thiếu thời gian; cần đọc lỗi edit và chuỗi request lặp trong trajectory. Request lặp là triệu chứng quan sát được, chưa chứng minh cơ chế nội tại gây lặp.

## E4B — đối chiếu workflow

A=incomplete; B=incomplete; C=incomplete. A/B thay đổi trạng thái runtime, hướng dẫn động và tập tool cho phép cùng nhau; nếu cải thiện thì chưa tách riêng tác dụng của từng thành phần. C có thêm harness hỗ trợ nộp và kiểm tra, nên pass ở C không đồng nghĩa model tự submit tốt hơn.

## 12B — đối chiếu workflow

A=incomplete; B=incomplete; C=local_pass. A/B thay đổi trạng thái runtime, hướng dẫn động và tập tool cho phép cùng nhau; nếu cải thiện thì chưa tách riêng tác dụng của từng thành phần. C có thêm harness hỗ trợ nộp và kiểm tra, nên pass ở C không đồng nghĩa model tự submit tốt hơn.

## 31B — đối chiếu workflow

A=incomplete; B=local_pass; C=local_pass. A/B thay đổi trạng thái runtime, hướng dẫn động và tập tool cho phép cùng nhau; nếu cải thiện thì chưa tách riêng tác dụng của từng thành phần. C có thêm harness hỗ trợ nộp và kiểm tra, nên pass ở C không đồng nghĩa model tự submit tốt hơn.

## Đính chính nguyên nhân 12B — lỗi harness đã quan sát

Trajectory runs/20261116T071557Z-8c31c62e cho thấy python3 -m unittest discover -s tests -v trả exit 0, nhưng phase vẫn verify: code cũ so sánh nguyên chuỗi với python -m unittest discover -s tests -v. Sau đó harness chặn lệnh vì lặp và dừng stalled. Đây là lỗi nhận diện verification của harness, không đủ cơ sở quy toàn bộ thất bại cho model. Nhánh code v2 công nhận alias interpreter và verbosity tương đương, vẫn giữ nguyên test target và yêu cầu code version không đổi. Đợt so sánh lớp mới sẽ kiểm chứng tác dụng.

## Các giả thuyết chưa được chứng minh

Độ phù hợp giữa model và prompt/tool schema, mất thông tin do compact context, và ảnh hưởng của quantization hoặc cấu hình suy luận có thể góp phần. Đợt này không thay đổi độc lập các yếu tố đó nên chưa gán lỗi cho chúng. Tốc độ benchmark riêng cũng không giải thích được mọi lỗi task.

## Cách xác minh tiếp

Giữ riêng lỗi sửa code, lỗi tool và lỗi kết thúc; chạy lặp trên nhiều issue cố định. Sau đó đổi từng yếu tố: prompt, compact context, tool schema, rồi cấu hình suy luận/quantization nếu đủ tài nguyên. Đối chiếu trên cùng ngân sách thời gian và thêm phép đo cùng ngân sách lượt/token; không gộp model tự nộp với harness hỗ trợ nộp.
