# Phân tích hint ladder v2 — 12B

Lượt riêng của 12B: sinh lại A+B+C (r0, temp 0), sau đó tối đa 2 vòng phản hồi công khai trên code tích lũy. Raw/API khớp 3/3.

| Vòng | Model làm gì | Kết quả |
|---|---|---|
| r0 | `[^> <]*`, giống hệt v1 (tái lập được ở temp 0) | Nhanh, nhưng trượt `test_attributes_before_href` và kiểm tra thuộc tính dài |
| r1 | Thấy lỗi test (cả traceback lẫn tên test), nhưng gửi `new_string` **giống hệt** `old_string` | Tool báo lỗi "No changes to apply", code giữ nguyên |
| r2 | Lặp lại y hệt r1 | Lỗi tool như trên |

**Kết luận cho 12B trên bài này:**

- Phản hồi công khai **không giúp được**. Dù prompt nói rõ test nào trượt và yêu cầu "make a different minimal repair", 12B chép lại đúng dòng hiện tại. Model không nối được tên test `attributes_before_href` với việc mình đã loại dấu cách trong character class.
- Cộng với v1, 12B đã thử 4 mức gợi ý và 2 vòng phản hồi mà chưa có bản sửa đạt. Nút thắt của 12B nằm ở bước điều chỉnh chính xác biểu thức. Thêm thông tin dạng văn bản chưa gỡ được.
- Nếu muốn tiếp tục với 12B, hướng hợp lý hơn là để harness làm phần tinh chỉnh. Ví dụ: sinh vài biến thể character class rồi để bộ test công khai chọn, hoặc chặn lượt sửa trùng (`old == new`) ngay tại harness và yêu cầu lại. Đây là thay đổi harness, không phải năng lực model.

Giới hạn: một bài, một quỹ đạo, temp 0. Không gộp với 31B.
