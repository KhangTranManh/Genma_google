# B1 — Edit guard: định nghĩa và replay offline

Module `scripts/harness/edit_guard.py`, unit test `tests/test_edit_guard.py` (8/8 đạt).

**Phân loại lệnh edit:**

| Trạng thái | Ý nghĩa | Xử lý |
|---|---|---|
| `ok` | Áp dụng được và có thay đổi | Đi tiếp |
| `noop` | `old_string == new_string`, hoặc file không đổi | **Gọi lại 1 lần**, không tính lượt |
| `out_of_region` | Sửa ngoài khối source được cấp | **Gọi lại 1 lần**, không tính lượt |
| `not_found` | Không tìm thấy `old_string` nguyên văn | **Gọi lại 1 lần**, không tính lượt |
| `ambiguous` | `old_string` xuất hiện nhiều lần | **Gọi lại 1 lần**, không tính lượt |
| `invalid` | Sai số lượng call, sai đường dẫn hoặc sai tham số | Không gọi lại |

Lời nhắc khi gọi lại chỉ mô tả lỗi cơ học. Nó không bao giờ chứa kết quả của bộ chấm.

**Replay offline** trên 71 call đã lưu (`replay.json`). Offline không gọi lại được model, nên đây chỉ là đếm số trường hợp guard sẽ bắt:

| Trạng thái | Số lần | Ở đâu |
|---|---|---|
| `noop` | 3 | 12B hint-ladder-v2 r1 và r2, 31B diagnosis-edit attempt_2 |
| `not_found` | 2 | 31B feedback-budget attempt_1, 12B diagnosis-edit attempt_1 |
| `out_of_region` | 1 | 12B role-split hypothesis_0 |
| `invalid` | 2 | 31B feedback-edit attempt_2 (truncated), 31B diagnosis-edit attempt_1 |

Như vậy 6/71 lượt sửa trước đây đã mất vì lỗi cơ học mà guard xử lý được. Tác dụng thật của việc gọi lại sẽ đo ở B3, khi chạy với model.
