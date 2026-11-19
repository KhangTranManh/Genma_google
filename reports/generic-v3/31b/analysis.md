# Generic pipeline v3 — 31B, 8 bài / 8 repo

Pipeline chung (method 31, thay đổi v3: kiểm tra tính hợp lệ của repro; xử lý trường hợp không gọi tool). Issue nguyên văn, không định nghĩa tay. Lần chạy bị ngắt một lần ở werkzeug và được chạy tiếp bằng `--resume`; phần dở dang lưu ở `werkzeug_3147.interrupted-*`.

| Bài | Khoanh đúng file | Repro hợp lệ | Harness chọn | Chấm chính thức (mẫu đúng / 4) |
|---|---|---|---|---|
| w3lib_264 | ✓ | ✓ | t0 | **resolved** (4/4) |
| click_3299 | ✓ | ✓ (lần 2; lần 1 import `semver` bị loại) | t0 | **resolved** (4/4) |
| markdown_1621 | ✗ | ✓ | — | 0/4 (model từ chối sửa vì vùng được khoanh sai) |
| werkzeug_3147 | ✓ | ✓ | — | 0/4 |
| tenacity_640 | ✓ | ✓ | — | 0/4 |
| humanize_334 | ✓ | ✓ | t0 | 0/4 (public đạt, test ẩn trượt) |
| packaging_1155 | ✓ | ✗ (3 lần, script đều exit 0) | t0 | 0/4 (public chỉ dựa vào test) |
| platformdirs_540 | ✓ | ✓ | t0 | 0/4 (public đạt, test ẩn trượt) |

**Theo public: 2/8 bài resolved**. v2 là 1/8, v1 là 1/8. Không còn trường hợp có mẫu đúng mà harness bỏ sót.

## So với v2

- **Click được gỡ đúng như dự kiến.** Lần viết repro đầu import `semver` (không có trong môi trường) nên bị loại; lần thứ hai tái hiện đúng lỗi. Cả 4 mẫu đều được chọn và chấm chính thức là resolved.
- **Markdown:** model trả lời bằng văn xuôi rằng excerpt chỉ là method trừu tượng. Đây là lý do có v4 (khoanh vùng lại 1 lần).

## Vấn đề còn lại

1. **Có 3 bài public đạt nhưng test ẩn trượt** (humanize, packaging, platformdirs). Harness chọn sai ở 3/8 bài. Kiểm tra công khai chưa phát hiện được bản sửa quá rộng hoặc thiếu phạm vi.
2. **Repro không tạo được** (packaging): script viết ra không kích hoạt được lỗi trên môi trường Python 3.13.
3. **Suy luận sửa sai** (werkzeug, tenacity): khoanh đúng, repro đúng, nhưng bản sửa không qua repro.
