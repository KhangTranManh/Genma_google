# Phân tích hint ladder v1 — 12B

Lượt riêng của 12B. Mỗi mức gọi model một lần, temperature 0, bắt đầu từ code gốc. Không có phản hồi hay thử lại. Raw và API khớp ở cả 4/4 lần sinh. Mọi tool call đều hợp lệ và `old_string` khớp nguyên văn. Lỗi nằm ở nội dung bản sửa, không nằm ở thao tác tool.

| Mức | Biểu thức model viết | Kết quả |
|---|---|---|
| Đối chứng | `<base\s+[^>]*?href` | Đổi sang lazy nhưng vẫn quét tới cuối chuỗi. Reproducer median 1,13 s, 30K timeout. Còn bậc hai. |
| A (cơ chế) | `<base\s+[^>]+?href` + thêm `re.DOTALL` | Vẫn bậc hai (1,13 s). Đổi thêm cờ không liên quan làm 7 test chức năng trượt (latin1…). |
| A+B (+nguyên tắc) | `<base\s[^>\s]*[^>]*?href` | Thêm một đoạn quét lồng nhau, chậm hơn cả gốc: 2K mất 0,75 s, 4K trở lên timeout. |
| A+B+C (+ví dụ) | `<base\s[^> <]*href` | Áp đúng ý "loại thêm ký tự mở" nên tuyến tính (30K: 1,4 ms). Nhưng model loại thêm cả **dấu cách**, nên thẻ có thuộc tính trước href không khớp. Trượt `test_attributes_before_href` và cả 3 ca thuộc tính dài. |

**Kết luận cho 12B trên bài này (0/4 đạt):**

- **Giải thích cơ chế (A) không đổi được hướng sửa.** Model vẫn dùng lazy quantifier như ở đối chứng. Biết lỗi là bậc hai không giúp 12B chọn đúng chỗ cần sửa.
- **Nguyên tắc ở mức thiết kế (B) cũng chưa đủ.** 12B không chuyển được câu "dừng ở đầu thẻ kế tiếp" thành một character class. Bản sửa còn làm hiệu năng tệ hơn.
- **Chỉ khi có ví dụ cùng loại (C), 12B mới chạm tới cơ chế đúng.** Nhưng model chép quá tay, đưa cả dấu cách vào lớp loại trừ, dù B đã dặn phải giữ thẻ có thuộc tính khác trước href. Đây là lỗi áp dụng chính xác, không phải lỗi thiếu hướng.
- Theo tiêu chí đã đặt trước ("cả A+B+C vẫn trượt" → khả năng là giới hạn của model với loại lỗi này), 12B rơi vào nhóm này. Riêng mức C cho thấy 12B có thể gần đạt khi có mẫu cụ thể. Bước hữu ích hơn với 12B là một vòng phản hồi ngắn từ test chức năng sau mức C, không phải thêm giải thích.

Giới hạn: một bài, một lần sinh mỗi mức, temperature 0. Đây là chẩn đoán, không phải tỷ lệ. Kết quả này không gộp với 31B.
