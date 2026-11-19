# Báo cáo thí nghiệm Gemma local

Cập nhật UTC: 2026-11-16T09:48:58.848496+00:00

Trạng thái điều phối: **complete**.

Các phương pháp được báo cáo riêng. Kết quả hiện dùng một issue tổng hợp URLKit;
đây là kiểm tra workflow local, chưa phải điểm cuộc thi hay benchmark nhiều repository.

**Khôi phục:** prompt_only_12b_v1 → prompt_only_12b_v2.
Bản trước dừng do lỗi khởi động model; kết quả cũ được giữ nguyên.
[Chi tiết khôi phục](recovery-20261116.md)

## Phần 1 — Đổi model, giữ prompt và workflow

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261115T185117Z-5ed36d41](../runs/20261115T185117Z-5ed36d41/manifest.json) | e4b | local_fail | 113.2 | 16 | 5874 | 3/6 |
| [20261115T190437Z-ec445846](../runs/20261115T190437Z-ec445846/manifest.json) | 12b | local_pass | 125.8 | 12 | 3104 | 6/6 |
| [20261115T191757Z-54afaf6b](../runs/20261115T191757Z-54afaf6b/manifest.json) | 31b | incomplete | 241.9 | 15 | 2455 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/model_sweep_v1/state.json).

## Phần 2 — Chỉ thay prompt (v2 sau khi sửa chuyển model)

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T002916Z-00ec3129](../runs/20261116T002916Z-00ec3129/manifest.json) | 12b | incomplete | 148.0 | 24 | 2699 | chưa đánh giá |
| [20261116T004205Z-40c4ff49](../runs/20261116T004205Z-40c4ff49/manifest.json) | 12b | local_pass | 124.3 | 12 | 3104 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/prompt_only_12b_v2/state.json).

## Phần 3 — Tự sửa code workflow trong container

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T022151Z-44147f53](../runs/20261116T022151Z-44147f53/manifest.json) | 12b / baseline | local_pass | 76.8 | 12 | 1591 | 6/6 |
| [20261116T022936Z-bb3c5e51](../runs/20261116T022936Z-bb3c5e51/manifest.json) | 12b / candidate | incomplete | 146.9 | 24 | 2707 | chưa đánh giá |

Quyết định candidate: **rejected_task_result**. Workflow đang dùng chưa bị ghi đè.

State và hash cố định: [state.json](../runs/pipeline/workflow_code_12b_v2/state.json).

## Chạy lại 31B và đối chứng 12B — ngân sách 900 giây

**Trạng thái:** complete

Lượt bổ sung dùng cùng prompt hướng dẫn phục hồi lỗi tools, 900 giây, 48 lượt và 96 thao tác cho cả ba model.
Giữ nguyên workflow. Không so trực tiếp với ngân sách 240 giây và prompt cũ ở phần 1.

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T024750Z-4ba0b972](../runs/20261116T024750Z-4ba0b972/manifest.json) | 31b | incomplete | 344.5 | 48 | 2125 | chưa đánh giá |
| [20261116T030440Z-921eab6d](../runs/20261116T030440Z-921eab6d/manifest.json) | 12b | incomplete | 230.0 | 48 | 3580 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/model_31b_retry_v1/state.json).

## Đối chứng E4B — cùng prompt và ngân sách 900 giây

**Trạng thái:** complete

Lượt bổ sung dùng cùng prompt hướng dẫn phục hồi lỗi tools, 900 giây, 48 lượt và 96 thao tác cho cả ba model.
Giữ nguyên workflow. Không so trực tiếp với ngân sách 240 giây và prompt cũ ở phần 1.

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T031312Z-7c7956c6](../runs/20261116T031312Z-7c7956c6/manifest.json) | e4b | incomplete | 423.4 | 48 | 23720 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/model_e4b_control_v1/state.json).

## Tốc độ sinh và VRAM — benchmark cố định

**Trạng thái:** complete

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/model_metrics_v1/state.json).

## A — Đối chứng workflow cũ trên ba model

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T064438Z-a5dae13e](../runs/20261116T064438Z-a5dae13e/manifest.json) | 31b | incomplete | 345.9 | 48 | 2125 | chưa đánh giá |
| [20261116T065237Z-2f2f1f79](../runs/20261116T065237Z-2f2f1f79/manifest.json) | 12b | incomplete | 230.9 | 48 | 3580 | chưa đánh giá |
| [20261116T065837Z-c3cb7105](../runs/20261116T065837Z-c3cb7105/manifest.json) | e4b | incomplete | 524.6 | 48 | 29997 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/progress_baseline_v1/state.json).

## B — Trạng thái và chống loop trên ba model

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T070957Z-325fe24c](../runs/20261116T070957Z-325fe24c/manifest.json) | 31b | local_pass | 220.2 | 18 | 1821 | 6/6 |
| [20261116T071557Z-8c31c62e](../runs/20261116T071557Z-8c31c62e/manifest.json) | 12b | incomplete | 103.3 | 17 | 1805 | chưa đánh giá |
| [20261116T071942Z-c13011dd](../runs/20261116T071942Z-c13011dd/manifest.json) | e4b | incomplete | 619.4 | 48 | 35579 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/progress_guard_v1/state.json).

## C — Kết thúc có xác minh trên ba model

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T073405Z-5be811c3](../runs/20261116T073405Z-5be811c3/manifest.json) | 31b | local_pass | 196.2 | 15 | 1775 | 6/6 |
| [20261116T073927Z-cd0ec631](../runs/20261116T073927Z-cd0ec631/manifest.json) | 12b | local_pass | 70.6 | 8 | 1543 | 6/6 |
| [20261116T074230Z-722f1299](../runs/20261116T074230Z-722f1299/manifest.json) | e4b | incomplete | 503.3 | 48 | 27613 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/progress_finish_v1/state.json).

## Hai model — đối chứng mới

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T081014Z-cda35fd0](../runs/20261116T081014Z-cda35fd0/manifest.json) | 12b | incomplete | 103.4 | 17 | 1805 | chưa đánh giá |
| [20261116T081403Z-38ed1f10](../runs/20261116T081403Z-38ed1f10/manifest.json) | 31b | local_pass | 220.0 | 18 | 1821 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/layers_control_v1/state.json).

## Hai model — chỉ đổi prompt

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T082234Z-4e2eecd8](../runs/20261116T082234Z-4e2eecd8/manifest.json) | 12b | local_pass | 155.4 | 15 | 3769 | 6/6 |
| [20261116T082726Z-7b29fe29](../runs/20261116T082726Z-7b29fe29/manifest.json) | 31b | local_pass | 145.9 | 12 | 1322 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/layers_prompt_v1/state.json).

## Hai model — chỉ đổi code harness

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T083442Z-27293526](../runs/20261116T083442Z-27293526/manifest.json) | 12b | local_pass | 110.2 | 16 | 2208 | 6/6 |
| [20261116T083839Z-b5e0a98a](../runs/20261116T083839Z-b5e0a98a/manifest.json) | 31b | local_pass | 137.6 | 12 | 1136 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/layers_code_v1/state.json).

## Hai model — chỉ đổi cấu hình context runtime

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T084445Z-865bc7cc](../runs/20261116T084445Z-865bc7cc/manifest.json) | 12b | incomplete | 184.4 | 17 | 3823 | chưa đánh giá |
| [20261116T084957Z-ed7f1600](../runs/20261116T084957Z-ed7f1600/manifest.json) | 31b | local_pass | 190.1 | 14 | 1344 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/layers_runtime_v1/state.json).

## Kết hợp — đối chứng code mới + prompt cũ

**Trạng thái:** not_started

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/combined_control_v1/state.json).

## Kết hợp — code mới + prompt mới

**Trạng thái:** not_started

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/combined_prompt_v1/state.json).

## Kết quả lịch sử

Đã giữ 9 lượt `legacy_mixed` riêng. Những lượt này thay đổi nhiều yếu tố;
không gộp vào kết luận của các thí nghiệm độc lập.

[Bảng lịch sử](../experiments/RESULTS.md)

## Giới hạn và bước tiếp theo

- Không gộp điểm của các phương pháp hoặc suy ra tác dụng riêng từ lượt thay đổi nhiều yếu tố.
- Một issue và một lần chạy mỗi cấu hình chưa đủ kết luận model hay phương pháp nào tốt hơn nói chung.
- Tiếp theo cần tập issue cố định từ nhiều repo, chạy lặp và kiểm tra tương thích harness chính thức.
- Phần tự sửa workflow dùng bản sao cách ly và đánh giá cặp; mọi cải thiện chỉ là kết quả sơ bộ trên bài mẫu.

[Bảng so sánh đủ tiêu chí cho ba model](model-comparison.md)

[So sánh A/B/C chống loop](anti-loop-comparison.md)


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


# So sánh kết hợp code + prompt: 12B và 31B

Đối chứng code revision 2 + recovery prompt so với code revision 2 + completion prompt. Tất cả dùng model tự submit, không bật harness nộp hộ.

| Model | Nhánh | Kết quả | Tự submit + pass | Giây | Lượt | Tools |
|---|---|---|---|---:|---:|---:|
| 12b | Code mới + prompt cũ | Chờ chạy | — | — | — | — |
| 12b | Code mới + prompt mới | Chờ chạy | — | — | — | — |
| 31b | Code mới + prompt cũ | Chờ chạy | — | — | — | — |
| 31b | Code mới + prompt mới | Chờ chạy | — | — | — | — |

URLKit tạo commit mới mỗi lượt (timestamp khác). So khớp nội dung bằng dataset hash đã đóng băng; giữ SHA gốc trong từng record. Repo thực vẫn so SHA chính xác.

## Đánh giá theo cặp

- 12b / Code mới + prompt mới: Chờ đủ cặp đối chứng/candidate.
- 31b / Code mới + prompt mới: Chờ đủ cặp đối chứng/candidate.

## Bằng chứng


## Kiểm tra thiết kế

Chưa phát hiện sai khác ngoài thiết kế.
