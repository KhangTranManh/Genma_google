# Generic pipeline v6 — 31B, 8 bài / 8 repo (`--evidence --extra-checks --feedback`)

| Bài | Harness chọn | Chấm chính thức | Mẫu đúng ở vòng 0 | Vòng phản hồi |
|---|---|---|---|---|
| w3lib_264 | t0 | **resolved** | 4/4 | không cần |
| markdown_1621 | t0 | **resolved** | 3/4 | s29 có chạy, không cứu được |
| click_3299 | t0 | **resolved** | 4/4 | không cần |
| werkzeug_3147 | — | 0/4 | 0/4 | 4 lần: 1 `not_found`, 3 edit hợp lệ nhưng vẫn trượt |
| tenacity_640 | — | 0/4 | 0/4 | 4/4 `not_found` (old_string bịa: dòng không có trong file) |
| platformdirs_540 | — (đúng) | 0/4 | 0/4 | 4/4 no-op |
| humanize_334 | t0 (sai) | 0/4 | 0/4 | không chạy (public đạt) |
| packaging_1155 | t0 (sai) | 0/4 | 0/4 | không chạy (public đạt; không có repro) |

**Chọn đúng: 3/8** (v5: 2/8; v3: 2/8). Chọn sai: 2/8 (humanize, packaging), giống v5.

## Nguồn gốc của mức tăng

- **Markdown được giải ngay ở vòng 0, không nhờ phản hồi.** Mẫu t0 viết đúng biểu thức của bản sửa gốc (`start + len(placeholder)`); ở v5, mẫu t0 viết `end`. Dù temperature 0, request khác nhau giữa hai lần chạy: bước Localize và ca kiểm tra được sinh lại, và vLLM không bảo đảm sinh lại y hệt. Vì vậy mức tăng 2→3 là **biến thiên giữa các lần chạy** cộng với khoanh vùng đúng nhờ bằng chứng, chưa phải hiệu quả của vòng phản hồi.
- **Vòng phản hồi cứu được 0/11 mẫu.**
  - tenacity: model chép `old_string` gồm những dòng không có trong file (bịa code).
  - platformdirs: model lặp lại đúng thay đổi cũ (no-op).
  - werkzeug: có sửa nhưng vẫn sai.

  Kết luận này khớp với B2: với 31B, phản hồi văn bản ít giúp được.

## Kết luận về pipeline chung

Phần đáng giữ:
- khoanh vùng theo bằng chứng (8/8 đúng file);
- kiểm tra tính hợp lệ của repro;
- ca kiểm tra do model viết (chặn được 1 lần chọn sai);
- guard.

Vòng phản hồi tốn thêm khoảng 1 lượt gọi model và 1 lần chấm cho mỗi mẫu trượt, nhưng chưa có tác dụng.

Ước lượng thật cần chạy lặp: 3/8 so với 2/8 nằm trong khoảng dao động giữa các lần chạy. Bước nên làm tiếp:
1. Chạy cấu hình v5 hoặc v6 thêm 1–2 lần để đo độ dao động.
2. Mở rộng tập dev lên khoảng 20 bài.
3. Đưa pipeline vào runtime nộp bài chính thức.
