# B4 v2 — 31B: reproducer theo hàm + lấy mẫu thích nghi + 1 vòng phản hồi

Batch riêng của 31B (method 29). Kết quả v1 không đổi.

| Bài | Số mẫu dùng | Kết quả |
|---|---|---|
| w3lib_266 | 1 | t0 vòng 0: `[^<]*`, qua public, **accepted** (giống v1) |
| w3lib_268 | 8 (hết ngân sách) | **0/8.** Vòng 0 luôn là `_tag_re` → `[^>]*?`. Vòng 1, sau khi thấy cả hai hàm chậm, luôn sửa thành `[^>]*` cho `replace_tags` (nhanh). Nhưng **cả 16 lượt đều không đụng tới `_tags_re`**, dù phản hồi ghi rõ `remove_tags` timeout và excerpt 2 có sẵn trong prompt |
| w3lib_271 | 5 | s5 vòng 0: `[^<]*` cho cả hai nhánh; **qua toàn bộ kiểm tra public** nên harness chọn. Bộ chấm ẩn: upstream test và growth đạt, nhưng **hidden differential lệch 2 ca** → không accepted |

**Kết quả chọn theo public: 1/3 bài accepted** (giống v1). Lần đầu tiên harness chọn một mẫu mà bộ chấm ẩn bác bỏ.

## Mẫu 271/s5

Hai ca lệch đều có `>` nằm **trong giá trị thuộc tính có nháy**, ví dụ `<div content=']ol>' ...>`. Code gốc (`[^>]*`) và upstream (`[^<>]*`) cùng coi `>` đầu tiên là kết thúc thẻ. `[^<]*` thì đi tiếp đến `>` cuối cùng trước `<` kế tiếp.

Về HTML, `>` trong giá trị có nháy là hợp lệ. Cách hiểu của mẫu này có thể "đúng hơn", nhưng nó đổi hành vi so với cả code gốc lẫn upstream. Theo định nghĩa đã đăng ký trước, mẫu không được accepted.

Public differential không bắt được vì các ca đó thuộc loại non-plain (có `<`/`>` trong giá trị). Muốn harness tự loại được loại này, public corpus phải chứa `>` trong giá trị có nháy. Việc đó hợp lệ, vì chỉ so với code gốc và không cần đáp án.

## Vòng phản hồi

| Bài | Tác động của vòng phản hồi |
|---|---|
| 268 | Có tác dụng một nửa: 8/8 mẫu chuyển `replace_tags` từ chậm sang nhanh. Cách sửa vẫn là `[^>]*`, chưa phải `[^<>]*`; ở `_tag_re` thì vẫn đủ nhanh và giữ hành vi |
| 271 | Không giúp: 3 lần no-op, 1 lần quay về lazy, 1 lần bỏ sửa |

## Kết luận

1. **Lỗi "không sửa đủ vùng" là ổn định và không tự hết** khi có phản hồi theo hàm. 31B cần được hướng dẫn rõ hơn ở mức harness, ví dụ: tách mỗi vùng thành một lượt Patch riêng, và chỉ đưa vùng đang gây chậm cho từng hàm.
2. **Corpus public cần thêm `>` trong giá trị có nháy** (đổi định nghĩa "plain"). Thay đổi này phải qua preflight: bản upstream phải lệch 0 ca. `[^<]*` là lỗi lặp lại ở 264, 266 và 271.
3. Mỗi bài cần nhiều lượt gọi model hơn: 268 dùng 8 mẫu × 2 vòng × (Diagnose + Patch). Lấy mẫu thích nghi chỉ có ích khi lỗi đến từ ngẫu nhiên, không có ích khi lỗi mang tính hệ thống.

Giới hạn: 3 bài cùng repo, cùng loại lỗi.
