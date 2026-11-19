# Báo cáo thí nghiệm Gemma local

Cập nhật UTC: 2026-11-18T08:12:59.174990+00:00

Đợt URLKit và audit gate đã hoàn tất. Harness xếp hạng mới và thí nghiệm gợi ý đang ở các mức triển khai nêu cuối báo cáo.

Báo cáo bao gồm URLKit tổng hợp, pilot trên ba issue repository và các thí nghiệm chẩn đoán sâu trên một issue đã quan sát. Các nhóm có điều kiện chạy và tiêu chí chấm riêng. Chưa có điểm Kaggle.

**Tóm tắt:** Trên URLKit, hỗ trợ kết thúc có xác minh giúp 12B và 31B nộp được bản sửa đạt kiểm tra local. Trên các issue repository, phần lớn lượt chạy chưa giải được bài. Khi host cung cấp chính xác đoạn code và thao tác, cả hai model sửa file đúng trong mọi điều kiện của bài kiểm tra có hướng dẫn. Khi phải tự suy ra phương án, chúng vẫn thường tạo được diff hợp lệ nhưng trượt kiểm tra hành vi. Audit gate chấm 9 bản sửa và không có bản nào đạt toàn bộ tiêu chí. [Chi tiết các đợt sau URLKit](#các-đợt-sau-urlkit)

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

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T095110Z-1b568551](../runs/20261116T095110Z-1b568551/manifest.json) | 12b | local_pass | 110.1 | 16 | 2208 | 6/6 |
| [20261116T095508Z-17560357](../runs/20261116T095508Z-17560357/manifest.json) | 31b | local_pass | 137.7 | 12 | 1136 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/combined_control_v1/state.json).

## Kết hợp — code mới + prompt mới

**Trạng thái:** complete

| Run | Model / biến thể | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T100127Z-9d8867f5](../runs/20261116T100127Z-9d8867f5/manifest.json) | 12b | local_pass | 103.3 | 14 | 2150 | 6/6 |
| [20261116T100516Z-7145d893](../runs/20261116T100516Z-7145d893/manifest.json) | 31b | local_pass | 215.6 | 17 | 1795 | 6/6 |

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
| 12b | Code mới + prompt cũ | local_pass | True | 109.01 | 16 | 16 |
| 12b | Code mới + prompt mới | local_pass | True | 102.178 | 14 | 14 |
| 31b | Code mới + prompt cũ | local_pass | True | 136.543 | 12 | 12 |
| 31b | Code mới + prompt mới | local_pass | True | 214.338 | 17 | 17 |

URLKit tạo commit mới mỗi lượt (timestamp khác). So khớp nội dung bằng dataset hash đã đóng băng; giữ SHA gốc trong từng record. Repo thực vẫn so SHA chính xác.

## Đánh giá theo cặp

- 12b / Code mới + prompt mới: Cả hai tự submit và pass; thời gian candidate trừ baseline = -6.8s. Một mẫu chưa chứng minh cải thiện ổn định.
- 31b / Code mới + prompt mới: Cả hai tự submit và pass; thời gian candidate trừ baseline = +77.8s. Một mẫu chưa chứng minh cải thiện ổn định.

## Bằng chứng

- [20261116T095110Z-1b568551](../runs/20261116T095110Z-1b568551/manifest.json)
- [20261116T095508Z-17560357](../runs/20261116T095508Z-17560357/manifest.json)
- [20261116T100127Z-9d8867f5](../runs/20261116T100127Z-9d8867f5/manifest.json)
- [20261116T100516Z-7145d893](../runs/20261116T100516Z-7145d893/manifest.json)

## Kiểm tra thiết kế

Chưa phát hiện sai khác ngoài thiết kế.

## Các đợt sau URLKit

### Pilot repository và thay đổi workflow

| Đợt | Cách chạy | Kết quả |
|---|---|---|
| Pilot runtime chính thức | Biên dịch cấu hình 12B và 31B, hiệu chuẩn ba issue `w3lib_264`, `packaging_1125` và `platformdirs_540`, rồi chạy agent trong runtime pilot. | Hai cấu hình biên dịch được, ba issue qua hiệu chuẩn. 0/6 lượt agent đạt. Chưa chấm Kaggle. [Chi tiết](official/integration-report.md) |
| Focused reading v1/v2 | R0 đối chứng, R1 đổi prompt đọc, R2 thêm skill. | V1 dừng sau lỗi runtime, dùng v2 để so sánh. Trên 18 lượt v2 có 3 patch đạt khi chấm, trong đó chỉ 31B/R2 trên `w3lib_264` tự hoàn tất. [V1](reading-v1/comparison.md) · [V2](reading-v2/comparison.md) |
| Staged YAML | Chia workflow thành các bước với tool riêng và so với giao diện phẳng. | Staged đạt 0/6. Đối chứng phẳng có 1 patch đạt khi chấm, trên 31B và `w3lib_264`, nhưng lượt đó chưa tự hoàn tất. Phân tích ghi nhận lỗi edit, chi phí giao diện skill và sửa quá hẹp. [So sánh](staged-v1/comparison.md) · [Phân tích](staged-v1/postmortem.md) |
| Simple direct | Đơn giản hóa giao diện tool và đối chứng trên cùng ba issue. | Qua 4/4 bài nhỏ về sửa và tạo file. Trên issue thực, nhánh simple đạt 0/6 và đối chứng đạt 1/6, ở 31B trên `w3lib_264`. [Kết quả](simple-v1/comparison.html) |

### Tách lỗi sinh tool call, thao tác edit và suy luận cách sửa

| Đợt | Cách kiểm tra và kết quả |
|---|---|
| Tool-call probe | So raw output, API và bản chạy lại parser trên cùng một lần sinh. 12B đúng 3/4, 31B đúng 4/4. Trong case 12B sai, raw output đã khác yêu cầu. [Kết quả](toolcall-probe-v1/comparison.md) |
| Tool-call stress | 24 capture trên direct ngắn, direct dài và skill. 12B đạt 3/4 ở mỗi nhánh, 31B đạt 4/4, 4/4 và 3/4. Parser replay khớp API 24/24. Hai case skill đổi tham số số thành chuỗi. Đợt này chỉ đo call, chưa đo tác động lúc thực thi tool. [Phân tích](toolcall-stress-v1/analysis.md) |
| Stepwise | Tách tìm vị trí, đọc, sửa, kiểm tra và nộp. Cả hai model tìm đúng file và biểu thức liên quan, dùng hết sáu lượt đọc mà chưa bàn giao được kết luận, rồi gặp lỗi khớp đoạn cần sửa. [Phân tích](stepwise-v1/analysis.md) |
| Edit excerpt và context/prompt | Khi được cấp chính xác đoạn code và thay đổi cần làm, cả 12B và 31B sửa đúng. Qua 12/12 cấu hình prompt và context đến 12K, cả 24 lần thực thi riêng raw/API đều tạo đúng file mong đợi. Bài đo này kiểm tra khả năng thực hiện edit theo chỉ dẫn. [Edit excerpt](edit-excerpt-v1/analysis.md) · [Context/prompt](context-prompt-v1/analysis.md) |
| Infer edit | Vẫn cấp vị trí và đoạn code, để model tự chọn cách sửa. Mỗi model tạo diff hợp lệ 3/3 và đạt kiểm tra hành vi 0/3. Thêm ngữ cảnh đến 12K không thay đổi kết quả quan sát. [Phân tích](infer-edit-v1/analysis.md) |
| Feedback edit | Gửi lại lỗi test và số liệu thời gian qua các lượt sửa. Cả hai model chưa có bản sửa đạt. Lượt cuối của 31B chạm trần 512 token và thiếu tool call hợp lệ. [Phân tích](feedback-edit-v1/analysis.md) |
| Ba chiến lược sửa | A tăng trần lên 1536 token, B tách chẩn đoán khỏi edit, C sinh ba ứng viên độc lập. Có 21 lượt gọi model và sáu ứng viên cuối. 0/6 đạt cả bộ chấm gốc và kiểm tra ngữ nghĩa bổ sung. A/12B qua bộ chấm gốc nhưng làm sai hành vi với thuộc tính hợp lệ dài. A/31B hết hiện tượng cắt output trong lượt này, song patch vẫn trượt hiệu năng. B phát biểu được một phần cơ chế nhưng bản sửa chưa thực hiện được. C sinh các biến thể gần nhau về thuật toán. [A](feedback-budget-v1/analysis.md) · [B](diagnosis-edit-v1/analysis.md) · [C](candidates-edit-v1/analysis.md) · [So sánh](repair-strategies-v1/analysis.md) |

### Harness tách vai và cách điều phối từng bước

Cùng một checkpoint Gemma thực hiện các vai qua những lượt gọi độc lập. Python quản lý bằng chứng, thứ tự ứng viên và việc chấm. Mỗi vai nhận các đầu vào được quy định cho vai đó.

1. **Chuẩn bị.** Chốt phiên bản code gốc, ngân sách, ca chẩn đoán và bộ chấm. Hiệu chuẩn trên code gốc và bản tham chiếu để xác nhận bộ chấm phân biệt được hai trạng thái. Lưu kết quả chấm độc lập ngoài prompt.
2. **Localize.** Model đề xuất tối đa ba giả thuyết, gồm vị trí, cơ chế và dự đoán trên các ca chẩn đoán. Python lưu bản dự đoán trước khi tiết lộ kết quả. Tín hiệu coverage/Ochiai có thể hỗ trợ xếp thứ tự. Trong đợt đo này coverage chỉ cho liên hệ yếu giữa dòng code và test.
3. **Đối chiếu.** Python so dự đoán với kết quả đo và ghi ca khớp, mâu thuẫn hoặc chưa xác định. Ở các lượt đã chạy, gate có thể chặn Patch. Nhánh Revise cho đúng một lượt sửa giả thuyết sau khi xem kết quả của bốn ca cũ, rồi đối chiếu dự đoán trên hai ca chưa tiết lộ kết quả.
4. **Patch.** Model nhận một giả thuyết đã chọn, code gốc và bằng chứng được phép xem. Mỗi ứng viên bắt đầu từ một bản code gốc sạch. Python kiểm tra tool call, áp dụng diff và ghi nhận diff lặp, output bị cắt hoặc lỗi hạ tầng.
5. **Đọc phản hồi.** Vai Review, khi được gọi, nhận kết quả cô đọng để nhận xét mức độ bằng chứng ủng hộ cơ chế ban đầu và trạng thái bản sửa. Đây là đầu ra tư vấn. Python ra quyết định dựa trên kiểm tra hành vi.
6. **Giữ, chọn và chấm cuối.** Patch được giữ khi đạt kiểm tra hành vi công khai và qua kiểm tra hồi quy chức năng/ngữ nghĩa. Luồng thông thường chỉ chấm độc lập ứng viên được chọn. Kết quả chấm cuối không quay lại bước chọn hay tạo thêm lượt sửa. Audit chấm từng ứng viên để đo tác động của gate.

| Đợt đã chạy | Kết quả |
|---|---|
| Role split | 14 lượt gọi, gồm 6 patch hợp lệ từ 6 giả thuyết. 31B tạo hai diff lặp. Không có ứng viên được giữ, nên bộ chấm cuối không chạy. Review đánh giá 5/6 giả thuyết là được ủng hộ, dù không có patch nào đạt điều kiện giữ. [Chi tiết](role-split-v1/analysis.md) |
| Role probes | 12B có ba giả thuyết và cả ba bị gate chặn. Với 31B, một giả thuyết được vào Patch và ứng viên trượt kiểm tra. [Chi tiết](role-probes-v1/analysis.md) |
| Revise hypothesis | Với 31B, cả ba giả thuyết sau revise khớp 4/4 kết quả đã xem và 1/2 kết quả chưa xem. Gate không cấp lượt Patch. Output Localize của 12B bị cắt ở 2048 token, nên không có giả thuyết hoàn chỉnh để chấm. [Chi tiết](revise-hyp-v1/analysis.md) |

### Audit gate và trạng thái thiết kế mới

Audit gọi lại vai Patch trên **9 hồ sơ đã lưu**, gồm **8 từng bị chặn** và **1 đối chứng từng được phép qua gate**. Mỗi hồ sơ sinh một patch mới từ code gốc. 9/9 lần sinh hợp lệ, raw/API khớp, tổng cộng 1.316 output token. Cả 9 ứng viên qua 67 test chức năng và kiểm tra thuộc tính dài, nhưng đều trượt cả kiểm tra hiệu năng công khai và độc lập.

Trong nhóm bị chặn, số patch đạt quan sát được là **0/8**. Tỷ lệ gate bỏ sót trong số các patch đạt **chưa xác định** vì không có patch đạt ở cả hai nhóm. Replay offline so thứ tự ban đầu, gate cũ và rank-only trên ba trajectory với ngân sách 1, 2 hoặc 3 lượt Patch. Cả 27 cấu hình đều dùng lại nhóm ứng viên này và không tìm được patch đạt. Replay đo độ bao phủ theo ngân sách trong dữ liệu đã có. Hiệu quả của rank-only trên lượt chạy mới vẫn chưa được đo. [Audit](gate-review-v1/audit-analysis.md) · [Replay](gate-review-v1/policy-replay.json)

| Phần | Cơ chế | Trạng thái |
|---|---|---|
| 1. Audit phản thực tế | Cho cả hồ sơ từng bị chặn và đối chứng viết patch, rồi chấm từng ứng viên theo cùng tiêu chí. | Hoàn tất 9/9. |
| 2. Rank-only | Ưu tiên nhiều dự đoán khớp rõ ràng, ít mâu thuẫn, rồi tín hiệu từ source và thứ tự gốc. Giữ đủ các giả thuyết hợp lệ trong hàng đợi. Cờ mâu thuẫn mạnh chỉ ghi nhận, quyền vào hàng đợi giữ nguyên. | Có hàm xếp hạng và replay offline. Chưa thử end-to-end với model. |
| 3. Gộp theo hành vi | Gộp các giả thuyết có vector dự đoán giống hệt trong cùng bộ ca và giai đoạn. Thử đại diện trước, giữ thành viên còn lại trong hàng đợi. Khi chỉ còn một vector, thiết kế cho phép một lượt yêu cầu hướng có dự đoán khác rõ ràng. | Có hàm gộp. Replay vector cho Role Probes 12B, Role Probes 31B và Revise 31B lần lượt là 1, 2 và 1 vector từ ba giả thuyết mỗi nhóm. Chưa chạy lượt yêu cầu giả thuyết mới. |
| 4. Ca phân biệt do model đề xuất | Model mô tả một ca và cam kết hai dự đoán trái nhau trước khi thấy kết quả. Kết quả quan sát được dùng để cập nhật thứ tự thử. | Có đặc tả/schema. Chưa có adapter thực thi và chưa đo với model. |
| 5. Giới hạn revise | Mặc định 0 lượt. Nhánh so sánh cho đúng một lượt và đo riêng trên các ca chưa tiết lộ kết quả. | Nhánh Revise cũ đã chạy. Chưa chạy thiết kế revise tùy chọn kết hợp với rank-only. |

### Thí nghiệm gợi ý và kết luận hiện tại

Phiên trước dừng sau khi xác định bốn mức hỗ trợ cho lượt Patch. **Chưa có lần chạy hay kết quả** cho các mức này.

| Nhánh dự kiến | Thông tin bổ sung |
|---|---|
| Đối chứng | Prompt cơ sở. |
| A | Giải thích cơ chế lỗi đã xác định. |
| A+B | Thêm nguyên tắc sửa ở mức thiết kế. |
| A+B+C | Nếu cần, thêm một ví dụ cùng loại từ bài khác. |

Ý tưởng là giữ nguyên checkpoint, ngân sách và bộ chấm để xem mức thông tin nào đủ giúp tạo patch đạt. Nếu A đạt còn đối chứng trượt, kết quả ủng hộ vai trò của chẩn đoán trong cấu hình đó. Nếu chỉ A+B đạt, hướng sửa bổ sung có giá trị trong bài thử. Một lượt mỗi mức chưa đủ để xác định giới hạn kiến thức của model hoặc hiệu quả trên các issue khác.

Bằng chứng hiện tại phân biệt được ba điểm nghẽn thực tế. Harness từng bỏ sót một lệnh kiểm tra tương đương và có thể ngăn nộp cả khi thu hồi được patch đạt. Tool call và edit có thể hoạt động đúng trong khi bản sửa vẫn sai về hành vi. Các lần chạy tách vai làm rõ hai lỗi đó, nhưng chưa tạo được bản sửa đạt trên bài chẩn đoán sâu. Các thí nghiệm cùng issue và các giả thuyết phát sinh trong cùng trajectory có quan hệ với nhau. Cần đọc tỷ lệ theo từng đợt, từng bộ chấm và tiêu chí tự hoàn tất.
