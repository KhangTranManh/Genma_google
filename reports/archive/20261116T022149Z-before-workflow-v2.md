# Báo cáo thí nghiệm Gemma local

Cập nhật UTC: 2026-11-16T00:47:41.070797+00:00

Trạng thái điều phối: **complete**.

Các phương pháp được báo cáo riêng. Kết quả hiện dùng một issue tổng hợp URLKit;
đây là kiểm tra workflow local, chưa phải điểm cuộc thi hay benchmark nhiều repository.

**Khôi phục:** prompt_only_12b_v1 → prompt_only_12b_v2.
Bản trước dừng do lỗi khởi động model; kết quả cũ được giữ nguyên.
[Chi tiết khôi phục](recovery-20261116.md)

## Phần 1 — Đổi model, giữ prompt và workflow

**Trạng thái:** complete

| Run | Model | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261115T185117Z-5ed36d41](../runs/20261115T185117Z-5ed36d41/manifest.json) | e4b | local_fail | 113.2 | 16 | 5874 | 3/6 |
| [20261115T190437Z-ec445846](../runs/20261115T190437Z-ec445846/manifest.json) | 12b | local_pass | 125.8 | 12 | 3104 | 6/6 |
| [20261115T191757Z-54afaf6b](../runs/20261115T191757Z-54afaf6b/manifest.json) | 31b | incomplete | 241.9 | 15 | 2455 | chưa đánh giá |

State và hash cố định: [state.json](../runs/pipeline/model_sweep_v1/state.json).

## Phần 2 — Chỉ thay prompt (v2 sau khi sửa chuyển model)

**Trạng thái:** complete

| Run | Model | Kết quả | Giây | Lượt agent | Output tokens | Test độc lập |
|---|---|---|---:|---:|---:|---|
| [20261116T002916Z-00ec3129](../runs/20261116T002916Z-00ec3129/manifest.json) | 12b | incomplete | 148.0 | 24 | 2699 | chưa đánh giá |
| [20261116T004205Z-40c4ff49](../runs/20261116T004205Z-40c4ff49/manifest.json) | 12b | local_pass | 124.3 | 12 | 3104 | 6/6 |

State và hash cố định: [state.json](../runs/pipeline/prompt_only_12b_v2/state.json).

## Phần 3 — Định nghĩa tự sửa code workflow

**Trạng thái:** definition_only

Đã định nghĩa phạm vi và quy trình kiểm chứng. Chưa thực thi model tự sửa code workflow;
không có số liệu thực nghiệm cho phần này.

[Tài liệu định nghĩa](../experiments/methods/03-workflow-code.md)

## Kết quả lịch sử

Đã giữ 9 lượt `legacy_mixed` riêng. Những lượt này thay đổi nhiều yếu tố;
không gộp vào kết luận của các thí nghiệm độc lập.

[Bảng lịch sử](../experiments/RESULTS.md)

## Giới hạn và bước tiếp theo

- Không gộp điểm của các phương pháp hoặc suy ra tác dụng riêng từ lượt thay đổi nhiều yếu tố.
- Một issue và một lần chạy mỗi cấu hình chưa đủ kết luận model hay phương pháp nào tốt hơn nói chung.
- Tiếp theo cần tập issue cố định từ nhiều repo, chạy lặp và kiểm tra tương thích harness chính thức.
- Phần tự sửa workflow cần bản sao mã nguồn cách ly và đánh giá cặp trước khi được bật.
