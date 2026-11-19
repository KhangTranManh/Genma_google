# B4 v3 — 31B: Patch theo từng vùng + public corpus v2

Batch riêng của 31B (method 30), tối đa 6 mẫu mỗi bài. Kết quả v1/v2 không đổi.

| Bài | Kết quả | Ghi chú |
|---|---|---|
| w3lib_266 | **Accepted**, mẫu t0 | Giống v1 và v2 |
| w3lib_268 | 0/6 | **Tiến bộ so với v2.** Khi mỗi vùng có lượt Patch riêng, 31B đã sửa `_tags_re`: 4/6 mẫu làm `remove_tags` nhanh, 3/6 làm cả hai hàm nhanh. Nhưng nó viết lại phần tên thẻ (`[a-zA-Z0-9-]+`, `[a-zA-Z]...`) thay vì chỉ thêm `<` vào lớp loại trừ, nên trượt test chức năng hoặc differential |
| w3lib_271 | 0/6 | Lazy `[^>]*?` ở 5/6 mẫu. s5 viết `[^<]*`, giờ bị **public** corpus v2 bắt. Vòng phản hồi: 3 lần `not_found` (old_string sai), 1 lần no-op, 2 lần trả về đúng code gốc |

**Tổng: 1/3 bài, không đổi qua v1, v2 và v3.** Harness không còn chọn sai mẫu: corpus v2 đã chặn kiểu `[^<]*`.

## Điều rút ra sau 3 vòng B4

1. Cơ chế harness hoạt động đúng như thiết kế:
   - tách vùng giải quyết lỗi "không sửa đủ chỗ";
   - public check theo hàm cho biết hàm nào còn chậm;
   - corpus v2 chặn được ứng viên lệch hành vi.
2. Phần còn thiếu là **kiến thức sửa đúng**. Có hai kiểu thất bại lặp đi lặp lại:
   - gặp `[^>]*` thì rơi về lazy `[^>]*?`;
   - khi buộc phải đổi thì đổi quá tay: viết lại tên thẻ, hoặc dùng `[^<]*` thiếu `>`.

   Cách sửa đúng (`[^<>]*`) chỉ xuất hiện khi pattern có sẵn dạng `[^>]*>`, như ở 264 và 266.
3. Với 31B ở loại lỗi này, thêm vòng phản hồi hay thêm mẫu cho lợi ích nhỏ. Hai lựa chọn có triển vọng hơn:
   - đưa vào bước Patch một **gợi ý cụ thể theo loại lỗi**, ví dụ "giữ nguyên tên thẻ; chỉ thêm `<` vào lớp ký tự đang quét", rồi kiểm tra lại trên bài mới;
   - chấp nhận giới hạn này và chuyển trọng tâm sang các loại lỗi khác (B5).

Giới hạn: 3 bài cùng repo, cùng loại lỗi; 6 mẫu mỗi bài.
