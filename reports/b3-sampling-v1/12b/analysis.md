# B3 — 12B: lấy 6 mẫu, harness lọc bằng kiểm tra công khai

Batch riêng của 12B. Có 2 prompt × 6 mẫu (temp 0,6, seed 1–6) = 12 lần sinh. Guard B1 trả `ok` cả 12/12, không có lượt gọi lại nào. Mọi lỗi dưới đây là lỗi nội dung bản sửa.

| Prompt | Biểu thức (số mẫu) | Kết quả kiểm tra công khai |
|---|---|---|
| A+B+C | `[^> <]*` (3) | Nhanh, nhưng trượt test và differential, giống v1/v2 |
| A+B+C | `[^<>\r\n]*` (1) | Nhanh, qua test, trượt differential (thẻ có xuống dòng) |
| A+B+C | `[^>\[\n\r]*` (1) | Vẫn chậm |
| A+B+C | `[^>\[<]*` (1, seed 4) | **Qua cả 3 kiểm tra công khai** → harness chọn. Hidden: **accepted** |
| A+G | `[^>\s]*\w*\s*href` (4) | Nhanh, qua test, trượt differential |
| A+G | `[^>\s]*\w*\s*[^>]*href` (2) | Vẫn chậm |

**Theo các bộ chấm đăng ký trước:** prompt A+B+C có 1/6 mẫu đạt và được harness chọn đúng chỉ bằng kiểm tra công khai. Bộ chấm ẩn xác nhận mẫu đó accepted. Prompt A+G có 0/6 mẫu đạt.

**Audit sau sự kiện** (`posthoc-special-chars.json`): mẫu được chọn `[^>\[<]*` loại thêm ký tự `[`. Đây là phần chép từ ví dụ C (`[^\[\]]`). Kết quả là thẻ hợp lệ như `<base title="[draft]" href="/a/">` không còn khớp, trong khi code gốc và upstream đều khớp. Corpus differential không có `[` trong bảng chữ cái nên bỏ sót. Đây là lỗ hổng bộ chấm thứ ba.

Nếu tính cả kiểm tra này, **12B đạt 0/12**. Không mẫu nào trong 12 mẫu khớp code gốc trên cả 4 ca ký tự đặc biệt mà vẫn đủ nhanh.

**Kết luận cho 12B:**

- Lấy nhiều mẫu cộng với lọc công khai **có thể** bắt được một bản "gần đúng" (1/6). Cách làm này có tác dụng thật: chọn đúng mẫu duy nhất qua công khai.
- Nhưng 12B không ổn định ở chỗ chọn đúng tập ký tự cần loại trừ. Nó thêm `[`, dấu cách, `\r\n`... từ ví dụ hoặc theo cảm tính. Bộ chấm chỉ tốt bằng độ phủ corpus của nó.
- Cần mở rộng corpus differential với toàn bộ ký tự ASCII in được trong giá trị thuộc tính. Việc này phải làm trước khi tin bất kỳ kết quả "accepted" nào ở B4, và preflight phải bắt được `[^>\[<]*`.

Giới hạn: một bài, 6 mẫu mỗi prompt. Không gộp với 31B.
