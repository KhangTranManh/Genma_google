# Bước 1 — Độ dao động giữa các lần chạy (31B, 8 bài dev)

Cấu hình: `--evidence --extra-checks` (v5). v6 dùng cùng cấu hình cộng một vòng phản hồi; vòng phản hồi không đổi lựa chọn nào (0/11), nên được tính như một lần quan sát thêm.

✓ = harness chọn mẫu và mẫu đó resolved (chấm chính thức); ✗ chọn sai = chọn mẫu qua public nhưng trượt chấm chính thức; · = không chọn mẫu nào.

| Bài | v5 | v6 (vòng 0 + phản hồi) | rep1 | rep2 |
|---|---|---|---|---|
| w3lib_264 | ✓ | ✓ | ✓ | ✓ |
| markdown_1621 | · | ✓ | · | · |
| werkzeug_3147 | · | · | · | · |
| tenacity_640 | · | · | · | · |
| humanize_334 | ✗ chọn sai | ✗ chọn sai | ✗ chọn sai | ✗ chọn sai |
| packaging_1155 | ✗ chọn sai | ✗ chọn sai | ✗ chọn sai | ✗ chọn sai |
| click_3299 | ✓ | ✓ | ✓ | ✓ |
| platformdirs_540 | · | · | · | · |
| **Chọn đúng** | **2/8** | **3/8** | **2/8** | **2/8** |
| Chọn sai | 2/8 | 2/8 | 2/8 | 2/8 |

**Kết quả:** chọn đúng 2–3/8, trung bình 2.25/8 qua 4 lần chạy.

- **Ổn định (cả 4 lần):** w3lib_264 và click_3299 luôn giải được. humanize_334 và packaging_1155 luôn bị chọn sai (public đạt, test ẩn trượt). werkzeug, tenacity và platformdirs luôn không có mẫu đúng.
- **Dao động:** chỉ markdown_1621 (giải được ở v6, trượt ở v5, rep1, rep2: 1/4). Mức 3/8 của v6 vì vậy là một lần may; ước lượng hợp lý cho cấu hình này là **khoảng 2/8 (25%)**, với một bài nằm ở ranh giới.
- **Chọn sai luôn là 2/8**, cùng hai bài. Đây là chỗ cải tiến rõ nhất: kiểm tra công khai vẫn chưa đủ chặt ở bài thiếu repro (packaging) và bài có yêu cầu ngầm (humanize: giá trị quá lớn vẫn phải báo lỗi).
