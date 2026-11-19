# B2 — 31B: tự chẩn đoán + checklist G + phản hồi differential công khai

Batch riêng của 31B. Có 2 nhánh × 4 quỹ đạo (temp 0; temp 0,6 với seed 17/29/43), mỗi quỹ đạo tối đa 2 vòng Patch. Lần chạy đầu dừng vì lỗi key trong worker trước khi gọi model. Đã sửa và chạy lại sạch; log lỗi giữ ở `runs/b2-selfdiag-v1-31b.failed-keyerror.log`.

## Kết quả

| Nhánh | Vòng 0 | Vòng 1 (sau phản hồi) | Accepted cuối |
|---|---|---|---|
| `selfdiag_G` t0 | `[^>]*?` (chậm) | Lặp nhiều call no-op đến khi bị cắt ở 1536 token → `invalid` | Không |
| `selfdiag_G` s17 | `[^>]*?` | `[^>]*?\bhref` (vẫn chậm) | Không |
| `selfdiag_G` s29 | **`[^<>]*`** | — | **Có** |
| `selfdiag_G` s43 | `[^>]*?` | Lặp no-op, bị cắt → `invalid` | Không |
| `hostA_G` ×4 | `[^<]*?` (nhanh, lệch 130 ca differential) | Quay về `[^>]*?` (hết lệch `>`, nhưng chậm lại) | Không ×4 |

**selfdiag_G đạt 1/4; hostA_G đạt 0/4.** Mẫu đạt là `[^<>]*`, trùng bản upstream. Biểu thức này cũng qua audit ký tự đặc biệt của B3.

## Điều rút ra

1. **Chẩn đoán không còn là nút thắt.** Cả 4 lần Diagnose của 31B đều xác định đúng span `[^>]*`, đúng điều kiện thất bại, đúng độ phức tạp bậc hai và đúng cơ chế backtracking. JSON parse được 4/4, không lần nào bị cắt. Tự chẩn đoán cho kết quả không kém A do host viết (1/4 so với 0/4).
2. **Nút thắt là bước Patch: chọn đúng tập ký tự loại trừ.** Dù có chẩn đoán đúng và checklist G, 31B vẫn thường rơi về lazy `[^>]*?`.
3. **Phản hồi differential chưa giúp được, thậm chí kéo lùi.** Ở hostA_G, 31B nhận 3 ví dụ rõ ràng:
   - `>` bị vượt qua ở 2 ví dụ (`<base target="_top">see href=...`);
   - `href` đầu tiên bị lấy thay vì cái cuối (`data-href`).

   Model sửa đúng một triệu chứng (thêm lại `>`) nhưng bỏ luôn phần loại `<`, nên quay về bản chậm. Nó không kết hợp được hai ràng buộc thành `[^<>]*`. Vòng sửa thay thế lỗi này bằng lỗi khác chứ không cộng dồn hiểu biết.
4. **Lỗi thao tác mới:** ở vòng phản hồi, 31B có lúc phát lặp lại nhiều call no-op cho đến khi bị cắt (2/8 vòng). Guard B1 xếp loại này là `invalid` vì có nhiều call, nên không gọi lại. Cần bổ sung luật: nếu mọi call đều giống nhau, coi là no-op và cho gọi lại.

## Hàm ý

- Hướng có triển vọng nhất cho 31B là **giữ phần đã đúng giữa các vòng**: harness tổng hợp các ràng buộc rút ra từ mỗi lần trượt (nhanh; không vượt `>`; lấy `href` cuối) thành danh sách ràng buộc tích lũy. Cũng có thể đổi sang kiểu lấy nhiều mẫu + lọc công khai như B3: ở đây có 1/4 mẫu đạt ngay từ vòng 0.
- Dữ liệu B2 và B3 gợi ý **lấy mẫu + lọc công khai** hiệu quả hơn **phản hồi lặp** với cả hai model trên bài này.

Giới hạn: một bài, 4 quỹ đạo mỗi nhánh. Checklist G được viết sau khi đã thấy bài này. Không gộp với 12B.
