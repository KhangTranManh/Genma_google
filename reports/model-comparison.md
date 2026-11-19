# Bảng so sánh E4B, 12B và 31B

Đợt đối chứng mới: cùng workflow, prompt phục hồi lỗi tools, issue URLKit và giới hạn **900 giây / 48 lượt / 96 thao tác**.
Không trộn với các lượt 240 giây hoặc prompt cũ. Đây chưa phải benchmark nhiều repo hay điểm thi.

| Model | Trạng thái | Nộp patch | Test công khai | Test độc lập | Giây | Lượt / tools | Input / output tokens | Lỗi edit | Benchmark token/s | TTFT ms | VRAM GPU0 / GPU1 MiB |
|---|---|---|---|---|---:|---|---|---:|---:|---:|---|
| e4b | incomplete | chưa | - | - | 423.4 | 48 / 44 | 126816 / 23720 | 8 | 67.1 | 54.5 | 12876 / 12876 |
| 12b | incomplete | chưa | - | - | 230.0 | 48 / 48 | 133807 / 3580 | 2 | 34.3 | 57.2 | 12884 / 12884 |
| 31b | incomplete | chưa | - | - | 344.5 | 48 / 48 | 123234 / 2125 | 2 | 15.4 | 85.5 | 12874 / 12874 |

## Cách đọc tiêu chí

- Nộp patch và test độc lập quyết định việc giải được bài mẫu; lượt fail, hết lượt hoặc timeout vẫn được giữ.
- Test công khai là kết quả bộ test trong repo. Test độc lập chạy trên bản sạch, ngoài context agent.
- Lỗi edit chỉ đếm thao tác edit_file bị từ chối; lỗi test lúc tái hiện bug không bị tính là lỗi edit.
- Benchmark tốc độ: một lượt warm-up rồi ba lượt cố định 128 output token, temperature 0, thinking tắt.
- TTFT là thời gian tới chunk nội dung/reasoning đầu tiên. Tốc độ là median end-to-end token/s của benchmark ngắn, không phải tốc độ toàn task.
- VRAM là mức lớn nhất được lấy mẫu trong benchmark, không phải peak của toàn lượt giải issue.
- Dấu “-” nghĩa là chưa có dữ liệu hoặc chưa tới bước đánh giá; không có nghĩa là đạt.
- Một issue và một lượt task mỗi model chưa đủ chứng minh ưu thế tổng quát.

## Bằng chứng

- 31b: [manifest](../runs/20261116T024750Z-4ba0b972/manifest.json), dừng vì `turn_limit`.
- 12b: [manifest](../runs/20261116T030440Z-921eab6d/manifest.json), dừng vì `turn_limit`.
- e4b: [manifest](../runs/20261116T031312Z-7c7956c6/manifest.json), dừng vì `turn_limit`.

Trạng thái đo hiệu năng: **complete**.
