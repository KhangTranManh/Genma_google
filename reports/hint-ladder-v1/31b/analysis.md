# Phân tích hint ladder v1 — 31B

Lượt riêng của 31B, chạy sau khi lượt 12B đã hoàn tất. Thiết kế giống hệt: mỗi mức gọi model một lần, temperature 0, bắt đầu từ code gốc, không có phản hồi hay thử lại. Raw và API khớp ở cả 4/4 lần sinh. Mọi tool call đều hợp lệ và `old_string` khớp nguyên văn.

| Mức | Biểu thức model viết | Kết quả |
|---|---|---|
| Đối chứng | `<base\s[^>]*?href` | Chỉ đổi sang lazy. Qua 67 test và kiểm tra thuộc tính dài, nhưng vẫn bậc hai: reproducer 1,13 s, 30K timeout. |
| A (cơ chế) | `<base\s[^>]*?href` | **Giống hệt đối chứng.** Giải thích cơ chế không làm thay đổi bản sửa. |
| A+B (+nguyên tắc) | `<base\s[^<>]*href` | **Đạt cả bốn kiểm tra.** Tuyến tính (30K: 1,4 ms), 67/67 test, bộ chấm độc lập, thuộc tính dài 0/200/1000. Trùng với bản sửa tham chiếu của host. |
| A+B+C (+ví dụ) | `<base\s[^<>]*href` | Đạt, cùng biểu thức với A+B. Ví dụ không thêm gì. |

**Kết luận cho 31B trên bài này:**

- Theo tiêu chí đặt trước, kết quả rơi vào nhánh **"chỉ A+B đạt"**. Thứ 31B thiếu là **hướng sửa**, không phải chẩn đoán. Biết lỗi là bậc hai do `[^>]*` (mức A) vẫn khiến model chọn lazy quantifier, là lối mòn ở mọi đợt trước. Khi được nói nguyên tắc "giới hạn mỗi lần dò trong thẻ của nó, không dùng giới hạn độ dài cố định", 31B tự viết ra đúng character class.
- Hệ quả cho harness: đầu tư thêm vào bước Localize/chẩn đoán (role split, gate, revise) khó cải thiện bài này với 31B. Hướng có triển vọng hơn là đưa **nguyên tắc sửa tổng quát theo loại lỗi** vào bước Patch, ví dụ với regex bậc hai: "giới hạn phạm vi mỗi lần thử, tránh lazy/length-limit". Cần kiểm tra nguyên tắc đó trên các issue khác để biết nó có tổng quát hay chỉ khớp bài này.
- Lưu ý mức độ: gợi ý B được viết khi đã biết đáp án và khá sát đáp án ("dừng ở đầu thẻ kế tiếp"). Kết quả cho thấy 31B **áp dụng được** hướng dẫn ở mức thiết kế, chưa cho thấy nó **tự tìm ra** hướng đó.

Giới hạn: một bài, một lần sinh mỗi mức, temperature 0. Đây là chẩn đoán, không phải tỷ lệ. Kết quả này không gộp với 12B.
