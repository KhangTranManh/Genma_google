# Generic pipeline v4 — khoanh vùng lại (chỉ chạy markdown_1621)

v4 chỉ thêm một điểm: nếu Patch ở t0 trả về văn xuôi mà không gọi tool, Localize chạy lại 1 lần, kèm lời giải thích của model. Các bài khác không bị ảnh hưởng, nên chỉ chạy lại markdown_1621.

| Bước | Kết quả |
|---|---|
| Localize lần 1 | `inlinepatterns.py::InlineProcessor.handleMatch` (sai; gold là `treeprocessors.py`) |
| Patch t0 | Từ chối ("đây chỉ là method trừu tượng") → kích hoạt khoanh vùng lại |
| Localize lần 2 | `inlinepatterns.py::LinkInlineProcessor` (vẫn sai file) |
| Patch 4 mẫu trên vùng mới | Edit hợp lệ 4/4; repro trượt 4/4; chấm chính thức 0/4 |

**Kết luận:** về cơ chế thì v4 hoạt động: model ngừng từ chối và có sửa thật. Nhưng nút thắt nằm ở chỗ khoanh vùng chỉ dựa vào chữ trong issue. Issue nói "inline links", còn lỗi nằm ở bộ duyệt chung `InlineProcessor.__applyPattern` trong `treeprocessors.py`, nơi quét lại từ đầu sau mỗi match. Không từ khóa nào trong issue dẫn tới đó.

**Hướng tiếp theo (chung cho mọi repo):** khoanh vùng dựa trên **bằng chứng khi chạy**. Chạy repro hợp lệ trên code gốc dưới `cProfile` (lỗi hiệu năng) hoặc lấy traceback (lỗi exception), rồi đưa danh sách hàm của repo tốn nhiều thời gian nhất hoặc nằm trên stack cho bước Localize. Ở markdown, repro đã hợp lệ ngay lần đầu, nên đủ dữ liệu cho cách này.
