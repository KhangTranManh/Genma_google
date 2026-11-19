# Differential oracle v2: corpus mở rộng và audit lại

**Vì sao có v2:** v1 bỏ sót `[^>\[<]*` (mẫu B3 12B seed 4), vì bảng chữ cái của corpus không có `[`.

**v2** (`scripts/graders/w3lib_264_differential_v2.py`):
- Thêm một ca cố định cho **mỗi ký tự ASCII in được**, cộng dấu cách, tab và xuống dòng, đặt trong giá trị thuộc tính. Mỗi ký tự có hai vị trí (giữa giá trị, hoặc là cả giá trị) và hai kiểu dấu nháy.
- Bảng chữ cái ngẫu nhiên có thêm toàn bộ dấu câu, tab và xuống dòng.
- Ca chứa `<` hoặc `>` trong giá trị vẫn là non-plain: chỉ chấm ở chế độ hidden, không chấm ở chế độ public.
- v1 giữ nguyên để tái lập các kết quả cũ.

**Preflight** (`preflight.json`, usable = true): code gốc và upstream lệch 0 ca. Mọi biến thể sai đều bị bắt, kể cả:
- `[^>\[<]*` lệch 443/511 ca (public/hidden);
- `[^<>\r\n]*` lệch 452/519 ca.

**Audit lại** (`audit.json`, 22 source khác nhau, kể cả ứng viên B2/B3):
- **`[^<>]*` vẫn là biểu thức duy nhất vừa giữ hành vi vừa nhanh.** Nó có trong B2 31B selfdiag s29, hint ladder 31B A+B/A+B+C, các đợt cho sẵn cách sửa, và các lượt agent dùng issue gốc có sẵn đáp án.
- Mẫu B3 12B được chọn (`[^>\[<]*`) giờ **trượt** cả public lẫn hidden. Kết luận "12B 0/12" từ audit sau sự kiện nay đã được bộ chấm đăng ký trước xác nhận.
- B3 AG `[^>\s]*\w*\s*[^>]*href` giữ được hành vi, nhưng vẫn chậm nên không accepted. Code gốc (edit no-op ở role-split) qua differential theo định nghĩa.

Từ bước này trở đi, mọi lượt chạy mới dùng v2.
