# B4 v1 — 31B: chuyển giao sang 3 issue regex cùng loại

Batch riêng của 31B: 3 bài × 4 mẫu (t0, seed 17/29/43). Mỗi mẫu tự chẩn đoán rồi Patch với checklist G. Guard B1 đa vùng. Harness chọn mẫu đầu tiên qua kiểm tra công khai.

| Bài | Biểu thức 31B viết | Accepted (audit) | Harness chọn |
|---|---|---|---|
| w3lib_266 `_meta_tag_re` | `[^<]*` ×4 | **4/4** | t0 → accepted |
| w3lib_268 `_tag_re` + `_tags_re` | Chỉ sửa `_tag_re` thành `[^>]*?` ×4, **không đụng `_tags_re`** | 0/4 | Không có |
| w3lib_271 `_build_remove_tags_pattern` | `[^>]*?` (lazy) ×2; thêm một nhánh `tag3` (nhanh nhưng lệch hành vi) ×1; t0 lặp no-op đến khi bị cắt, 2 lần | 0/4 | Không có |

**Tổng: 1/3 bài được giải và chọn đúng** (4/12 mẫu accepted).

## Kiểm tra thêm với w3lib_266

`[^<]*` khác bản upstream `[^<>]*`: nó có thể kéo dài tag qua `>` cho đến `<` kế tiếp. Ở bài 264 đây là lỗi thật. Ở `get_meta_refresh`, tag sau đó còn được lọc bằng `_meta_refresh_re` (`<meta\s[^>]*...`), và regex này dừng ở `>` đầu tiên.

Ba input nhắm thẳng vào chỗ khác biệt (text chứa `>` và thuộc tính refresh giả sau một thẻ meta) cho kết quả giống hệt code gốc và upstream. Vì vậy kết quả accepted ở đây là hợp lệ **ở mức hàm public**. Nếu sau này `_meta_tag_re` được dùng ở nơi khác, khác biệt có thể lộ ra.

## Nhận xét

1. **Chẩn đoán vẫn tốt.** Cả 12 lần đều ra JSON hợp lệ và chỉ đúng span, kể cả `.*?` ở 268.
2. **Chuyển giao được khi hình dạng lỗi giống 264** (`[^>]*` đứng ngay trước `>`): 266 đạt 4/4.
3. **Không chuyển giao khi hình dạng khác:**
   - 268 có `.*?` lazy và **hai** vùng. 31B chỉ sửa một vùng ở cả 4 mẫu, dù prompt nói rõ có 2 excerpt và cho phép 2 call. `remove_tags` vẫn timeout. Đây là lỗi "sửa chưa đủ chỗ", khác với lỗi chọn sai ký tự.
   - 271 dùng pattern verbose có backreference. 31B lại rơi về lazy `[^>]*?`, đúng lối mòn ở 264.
4. **Guard:** 271/t0 lặp 11 call no-op đến khi bị cắt. Guard nhận ra là no-op và gọi lại 1 lần, nhưng lần gọi lại lặp y hệt. Gọi lại đơn thuần không phá được vòng lặp này ở temperature 0.

## Hàm ý

- Cần một bước kiểm tra "mỗi vùng được cấp có được sửa không" khi issue nêu nhiều hàm. Có thể đưa vào public check: reproducer của **từng** hàm trong issue.
- Kiểu lỗi lazy fallback xuất hiện ở mọi bài mà pattern không có sẵn `[^>]`. Checklist G (mục 2 đã nói lazy không giúp) chưa đủ để chặn. Nên thử một public check rẻ, "reproducer phải nhanh", **trước** khi chọn mẫu, rồi lấy thêm mẫu nếu chưa có mẫu nào đạt (thích nghi theo ngân sách).

Giới hạn: 3 bài cùng repo, cùng loại lỗi; 4 mẫu mỗi bài. Không gộp với 12B.
