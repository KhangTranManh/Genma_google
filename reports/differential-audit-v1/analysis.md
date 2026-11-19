# B0 — Differential oracle và audit lại ứng viên lịch sử

## Bộ chấm

Bộ chấm `scripts/graders/w3lib_264_differential.py` dùng một corpus cố định (seed 264): 1.515 ca HTML hợp lệ và gần hợp lệ, trong đó có 15 ca viết tay. Corpus phủ các trường hợp: thuộc tính dài, `data-href`/`xhref`, thẻ đã đóng kèm text chứa `href=`, nhiều thẻ base, comment, khác hoa/thường, xuống dòng, `<` hoặc `>` trong giá trị thuộc tính, thẻ chưa đóng.

- **Public** (harness được dùng, không cần đáp án): trên các ca "plain" (thẻ đóng đúng, giá trị thuộc tính không chứa `<`/`>`), ứng viên phải trả **giống hệt code gốc**.
- **Hidden** (chỉ để chấm): trên mọi ca, ứng viên phải giống code gốc **hoặc** giống bản upstream `[^<>]*`. Bản upstream cũng đổi hành vi khi giá trị thuộc tính chứa `<`, và upstream đã chấp nhận thay đổi đó.
- Ca nào chạy quá 0,5 s đều tính là trượt.

## Preflight (`preflight.json`, usable = true)

| Biến thể | Public (số ca lệch) | Hidden (số ca lệch) |
|---|---|---|
| Code gốc | Đạt (0) | Đạt (0) |
| Upstream `[^<>]*` | Đạt (0) | Đạt (0) |
| `[^<]*` (31B A+G) | Trượt (2) | Trượt (32) |
| `[^<]*?` | Trượt (130) | Trượt (178) |
| `[^> <]*` (12B ABC) | Trượt (692) | Trượt (803) |
| `[^>]*?` (lazy) | Trượt (128) | Trượt (151) |
| `[^>]{0,100}?` | Trượt (449) | Trượt (502) |

Phát hiện phụ: lazy `[^>]*?` cũng đổi ngữ nghĩa. Khi thẻ có `data-href="a" href="b"`, nó lấy `href` **đầu tiên** thay vì cái cuối như bản gốc. 67 test hiện có không phủ trường hợp này.

## Audit lại (`audit.json`)

Audit gồm 161 ứng viên đã lưu, gộp còn 16 source khác nhau. Mọi patch đều áp dụng được, kể cả các patch agent sửa nhiều file. Kết quả cũ không bị sửa.

- **Chỉ một biểu thức đạt bộ chấm: `[^<>]*`.** Nó đến từ ba nguồn:
  - Các đợt host cho sẵn cách sửa (edit-excerpt, context-prompt, infer-edit `explicit_fix`).
  - Hint ladder 31B mức A+B và A+B+C.
  - Các lượt agent 31B ở reading-v2, simple-v1 và staged-v1. Lưu ý: các lượt này dùng **issue gốc của upstream, trong đó có sẵn câu "Changing `[^>]` to `[^<>]` fixes this case"**. Đây là gợi ý trực tiếp, không phải tự suy luận.
- Ngoài ra có một ứng viên trùng code gốc (role-split 12B, edit không đổi gì). Ứng viên này qua bộ chấm hành vi theo định nghĩa, nhưng không sửa được hiệu năng.
- Mọi biểu thức khác đều lệch ngữ nghĩa so với code gốc trên input hợp lệ, gồm lazy, `{0,100}`, `[^<]*`, `[^> <]*`, `[^>]+?` và các biến thể khác. Phần lớn số này vốn đã trượt hiệu năng.
- **4 ứng viên 31B A+G từng "accepted" ở hint ladder v2 bị loại bởi oracle mới.** Kết luận "A+G đạt 4/4" chỉ đúng theo 4 bộ chấm cũ. Theo bộ chấm mới, A+G đạt 0/4.

## Hệ quả

- Từ B2 trở đi, `accepted` = 4 bộ chấm cũ **cộng** hidden differential. Harness được dùng chế độ public.
- Điều kiện công bằng của chế độ public đã kiểm chứng: bản upstream lệch 0 ca plain.
