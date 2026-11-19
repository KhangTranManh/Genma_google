# Generic pipeline v2 — 31B, 8 bài / 8 repo

Pipeline chung (method 31), issue nguyên văn, không định nghĩa tay cho từng bài. Batch `generic-v1` giữ nguyên (5/8 bài hỏng ở bước tìm mã nguồn do harness).

| Bài | Khoanh đúng file | Repro hợp lệ | Public chọn | Chấm chính thức | Ghi chú |
|---|---|---|---|---|---|
| w3lib_264 | ✓ | ✓ | t0 | **resolved** (4/4) | Issue có sẵn gợi ý sửa |
| markdown_1621 | ✗ (inlinepatterns, gold treeprocessors) | ✓ | — | 0/4 | Model trả lời văn xuôi, **không gọi tool** (0 call) |
| werkzeug_3147 | ✓ | ✓ | — | 0/4 | Regex mới vẫn bắt buộc có `.` → repro đúng, model sai |
| tenacity_640 | ✓ | ✓ | — | 0/4 | Sửa sai cơ chế (raise ngay trong vòng lặp) |
| humanize_334 | ✓ | ✓ | t0 | 0/4 | Bắt OverflowError quá rộng; public không phát hiện |
| packaging_1155 | ✓ | ✗ | t0 | 0/4 | Không tạo được repro; public chỉ dựa vào test → chọn sai |
| click_3299 | ✓ | ✗ (thực ra) | — | **4/4 resolved nhưng public loại** | Repro trượt vì `ModuleNotFoundError: semver`, harness lại coi là hợp lệ |
| platformdirs_540 | ✓ | ✓ | t0 | 0/4 | Chỉ sửa `user_state_dir`; gold sửa mọi thư mục XDG (2 file) |

**Theo public: 1/8 resolved. Có ít nhất 1 mẫu đúng: 2/8 bài** (thêm click).

## Lỗi harness đã thấy (sửa ở v3)

1. **Repro trượt vì môi trường bị tính là hợp lệ.** Các lỗi ImportError, SyntaxError, NameError… trong chính `repro.py` phải bị coi là repro hỏng, và model được yêu cầu viết lại. Riêng lỗi này đã làm mất click (4 bản sửa đúng bị loại).
2. **Model không gọi tool** (0 call) bị xếp nhầm là "no-op", với lời nhắc sai ngữ cảnh. Cần một trạng thái riêng, kèm lời nhắc "phải gọi edit_file".

## Giới hạn còn lại (không phải lỗi harness)

- **Public check yếu:** humanize, packaging và platformdirs đều qua public nhưng trượt test ẩn. Repro chỉ kiểm tra đúng một ca trong issue; test hiện có thì không phủ hành vi mới. Mẫu sửa quá rộng hoặc sửa thiếu vẫn lọt.
- **Sửa thiếu phạm vi:** ở platformdirs, issue nói về `user_state_dir` nhưng tinh thần là mọi biến XDG. Model chỉ sửa đúng chỗ được nêu.
- **Suy luận sai:** werkzeug, tenacity.
