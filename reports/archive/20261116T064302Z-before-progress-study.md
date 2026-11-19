# Báo cáo thí nghiệm Gemma local

Cập nhật UTC: 2026-11-16T06:42:03.528466+00:00

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

**Trạng thái:** not_started

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/progress_baseline_v1/state.json).

## B — Trạng thái và chống loop trên ba model

**Trạng thái:** not_started

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/progress_guard_v1/state.json).

## C — Kết thúc có xác minh trên ba model

**Trạng thái:** not_started

Chưa có lượt chạy được lưu.

State và hash cố định: [state.json](../runs/pipeline/progress_finish_v1/state.json).

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
