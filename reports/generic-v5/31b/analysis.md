# Generic pipeline v5 — 31B, 8 bài / 8 repo (`--evidence --extra-checks`)

| Bài | Khoanh đúng file | Repro | Ca kiểm tra giữ lại | Harness chọn | Chấm chính thức |
|---|---|---|---|---|---|
| w3lib_264 | ✓ | ✓ | 5/8 | t0 | **resolved** (4/4) |
| click_3299 | ✓ | ✓ | 6/8 | t0 | **resolved** (4/4) |
| markdown_1621 | **✓ (mới)** `treeprocessors.__applyPattern` | ✓ | 7/8 | — (đúng) | 0/4 |
| werkzeug_3147 | ✓ | ✓ | 4/8 | — (đúng) | 0/4 |
| tenacity_640 | ✓ | ✓ | 5/6 | — (đúng) | 0/4 |
| platformdirs_540 | ✓ | ✓ | 7/7 | **— (đúng; v3 chọn sai)** | 0/4 |
| humanize_334 | ✓ | ✓ | 8/8 | t0 (sai) | 0/4 |
| packaging_1155 | ✓ | ✗ | 6/9 | t0 (sai) | 0/4 |

**So với v3:**

| Chỉ số | v3 | v5 |
|---|---|---|
| Khoanh đúng file | 7/8 | **8/8** |
| Chọn đúng (resolved) | 2/8 | 2/8 |
| Chọn sai (qua public, trượt test ẩn) | 3/8 | **2/8** |

## Hai thay đổi có tác dụng thật

1. **Bằng chứng khi chạy sửa đúng chỗ ở markdown.** Profiler chỉ thẳng `__applyPattern`. Model sửa đúng dòng của bản sửa gốc (`return …, True, 0`), nhưng dùng `end` thay vì `start + len(placeholder)`. Kết quả là repro đã nhanh, nhưng ca `preserve_basic_link_rendering` bắt được lỗi hiển thị link. Bản sửa chỉ còn cách đáp án một biểu thức.
2. **Ca kiểm tra do model viết chặn được chọn sai ở platformdirs.** Bốn ca `fixed_xdg_state_home_relative_*` trượt với bản sửa thiếu phạm vi, nên harness không chọn nữa.

## Còn lại

- **humanize:** 8 ca đều được giữ nhưng không ca nào nói "giá trị quá lớn vẫn phải báo lỗi". Model không suy ra được yêu cầu này từ issue.
- **packaging:** vẫn không tạo được repro. Ca kiểm tra không thay được repro.
- **werkzeug, tenacity, markdown:** đã có tín hiệu công khai cụ thể (ca nào trượt, thông báo lỗi), nhưng pipeline chưa đưa tín hiệu đó lại cho model.

**Hướng tiếp theo:** thêm **một vòng sửa có phản hồi** cho mẫu trượt public. Vòng này cho model xem kết quả repro, các ca kiểm tra trượt kèm thông báo lỗi, và test mới hỏng, rồi sửa tiếp trên bản đã sửa. Markdown là ứng viên rõ nhất.
