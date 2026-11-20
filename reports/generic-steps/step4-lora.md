# Bước 4 — Pilot QLoRA trên Gemma 4 12B

Ngày 20-11-2026 (UTC). Train hoàn tất lúc 10:09 và cả hai lượt đánh giá hoàn tất lúc 11:47. Code dùng cho pilot ở commit `5144869`.

## Dữ liệu và huấn luyện

- Pipeline dựng 479 mẫu từ bản vá FreshSWE công khai thuộc 32 repo. Cả 479 mẫu tái tạo được bản vá gốc theo kiểm tra của bộ dựng dữ liệu. Mã bài không trùng với hai danh sách dev gồm 8 và 20 bài.
- Trainer nhận 477 mẫu trong giới hạn chuỗi 8.192 token, chia thành 454 mẫu train và 23 mẫu giữ lại. Train một epoch, rank 16, gradient accumulation 8, seed 0, trên hai NVIDIA A16.
- Hoàn thành 57 bước trong khoảng 181 phút tính theo log vòng train. Loss trên tập giữ lại giảm từ 1,1223 trước khi train xuống 0,5456 ở bước 10 và 0,4495 ở bước 57.
- Adapter được train trên base NF4 và phục vụ thành công qua vLLM với base W4A16.

Xem [thống kê dữ liệu](../generic-12b-lora-v1/training/dataset-summary.json), [cấu hình train](../generic-12b-lora-v1/training/config.json), [loss từng bước](../generic-12b-lora-v1/training/metrics.jsonl) và [log hàng đợi](../generic-12b-lora-v1/training/queue.log).

## Đánh giá trên 8 bài dev

Cả hai lượt dùng cùng danh sách bài, cùng phiên bản pipeline và cùng cờ `--evidence --extra-checks`. Điểm tính theo bản vá pipeline chọn và kết quả chấm ẩn.

| Cấu hình | Giải đúng | Chọn bản vá sai | Thời gian |
|---|---:|---:|---:|
| 12B + LoRA | 1/8 | 2/8 | 43 phút 51 giây |
| 12B gốc | 1/8 | 1/8 | 52 phút 54 giây |

Cả hai giải đúng `w3lib_264`. LoRA chọn bản vá sai ở `humanize_334` và `platformdirs_540`, còn 12B gốc chọn bản vá sai ở `tenacity_640`. Loss giảm trong quá trình train nhưng điểm giải bài không tăng trong pilot này. Mốc [pipeline 31B v5](step1-variance.md) là 2/8.

- 12B + LoRA — [bảng kết quả](../generic-12b-lora-v1/12b/summary.md), [kết quả từng mẫu](../generic-12b-lora-v1/12b/state.json), [bản vá được chọn](../generic-12b-lora-v1/12b/selected-patches/)
- 12B gốc — [bảng kết quả](../generic-12b-base/12b/summary.md), [kết quả từng mẫu](../generic-12b-base/12b/state.json), [bản vá được chọn](../generic-12b-base/12b/selected-patches/)

Kết quả này là của pilot nội bộ. Điều khoản về việc dùng bản vá FreshSWE công khai làm dữ liệu huấn luyện cho bài nộp vẫn chưa được xác nhận.
