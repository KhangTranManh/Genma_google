# B4 v1 — 12B: chuyển giao sang 3 issue regex cùng loại

Batch riêng của 12B, chạy sau khi 31B xong: 3 bài × 6 mẫu (t0 + seed 17/29/43/5/11), cùng quy trình với 31B. Guard trả `ok` ở 18/18 lần. Mọi lỗi đều là lỗi nội dung bản sửa.

| Bài | Biểu thức 12B viết | Accepted |
|---|---|---|
| w3lib_266 | `[^>]+` ×6 (vẫn chậm) | 0/6 |
| w3lib_268 | `_tag_re` thành `[^>]*` ×6 (thiếu `<`). Có 1 mẫu sửa cả `_tags_re` nhưng cũng thiếu `<` | 0/6 |
| w3lib_271 | 6 biến thể khác nhau, sửa ở phần **nội dung** `.*?` thay vì phần thuộc tính: `[^>]*?`, lookbehind `(?<!<)`, tempered `(?:(?!<tag).)*?`. Phần lớn làm hỏng test hoặc lệch hành vi | 0/6 |

**Tổng: 0/3 bài, 0/18 mẫu.** Không mẫu nào qua cả reproducer công khai.

Nhận xét:

- 12B chẩn đoán ra JSON 16/18 lần. Nhưng ở 271 nó khoanh nhầm vùng gây lỗi (phần nội dung giữa hai thẻ thay vì phần thuộc tính `[^>]*`).
- Ở 266 và 268, 12B chỉ đổi lượng từ (`*` → `+`) hoặc đổi `.*?` → `[^>]*`. Nó không bao giờ thêm `<` vào lớp loại trừ. Cả 6 mẫu cho cùng một ý, nên lấy thêm mẫu khó giúp được.
- Cùng với hint ladder, B2/B3 và B4, 12B chưa có bản sửa nào đạt trên 4 bài regex. Đề xuất dừng đầu tư 12B cho loại lỗi này, hoặc chỉ dùng 12B ở các vai không cần chọn cách sửa.

Giới hạn: 3 bài cùng repo, 6 mẫu mỗi bài. Không gộp với 31B.
