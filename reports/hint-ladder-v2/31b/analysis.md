# Phân tích hint ladder v2 — 31B

Lượt riêng của 31B, 9 lần sinh. Raw/API khớp 9/9, mọi tool call hợp lệ. `accepted` theo 4 bộ chấm đăng ký trước. Cột "Giữ ranh giới thẻ" là audit **sau sự kiện** (`posthoc-tag-boundary.json`), không đổi kết quả chấm gốc.

| Nhánh | Temp | Biểu thức | Accepted | Giữ ranh giới thẻ |
|---|---|---|---|---|
| B (không có A) | 0 | `[^>]*?` | Không, vẫn bậc hai | Có |
| G (checklist chung, không có A) | 0 | `[^>]*?` | Không, vẫn bậc hai | Có |
| A+G | 0 | `[^<]*?` | **Có** | **Không** |
| A+B seed 17 | 0,6 | `[^<>]*` | **Có** | Có |
| A+B seed 29 | 0,6 | `[^< >]*` | Không, loại cả dấu cách nên hỏng thẻ có thuộc tính trước href | Có |
| A+B seed 43 | 0,6 | `[^<>]*` | **Có** | Có |
| A+G seed 17 / 29 / 43 | 0,6 | `[^<]*?`, `[^<]*?`, `[^<]*` | **Có ×3** | **Không ×3** |

Gộp với v1 (A+B ở temp 0 đạt), trên cùng bài và cùng model:

- **Cần cả cơ chế lẫn hướng sửa.** Chỉ B, hoặc chỉ G, đều cho lại lối mòn `[^>]*?`. Riêng A cũng vậy (v1). Chỉ khi có đủ "vì sao chậm" và "sửa theo hướng nào", 31B mới đổi được character class.
- **A+B ổn định ở mức 3/4** (temp 0 + 2/3 seed). Lần trượt lặp lại đúng lỗi của 12B: loại thêm dấu cách.
- **A+G (checklist không viết theo đáp án) đạt 4/4 theo bộ chấm**, nhưng cả 4 dùng `[^<]*`, tức chỉ loại `<` mà không loại `>`. Audit sau sự kiện cho thấy biểu thức này bắt nhầm `href` nằm **ngoài** thẻ base đã đóng, ví dụ `<base target="_top">see href="http://x/"`. Cả code gốc lẫn bản tham chiếu `[^<>]*` đều không khớp trường hợp này. Đây là lỗ hổng thứ hai của bộ chấm (lần trước là thuộc tính dài). Checklist chung đưa 31B tới đúng loại cách sửa, nhưng chưa đủ để giữ đúng ngữ nghĩa cũ.

**Hàm ý cho harness:**

1. Một checklist sửa lỗi theo loại lỗi, kèm chẩn đoán cơ chế, là đòn bẩy rõ nhất cho 31B trên bài này. Nó đổi kết quả từ 0 lên 4/4 theo bộ chấm.
2. Cần thêm một bước kiểm tra "giữ hành vi cũ" do harness sinh, ví dụ chạy song song regex cũ và mới trên các input hợp lệ hoặc gần hợp lệ. Cả hai lỗ hổng bộ chấm đến nay đều là thay đổi ngữ nghĩa mà test hiện có không phủ.
3. Chẩn đoán A ở đây do host viết. Muốn harness tự động, model phải tự sinh được A. Đó là đúng phần các đợt Localize trước chưa làm ổn.

Giới hạn: một bài, 3 seed mỗi nhánh. Audit ranh giới thẻ được viết sau khi đã thấy biểu thức, nên không dùng để so lại với v1 như một bộ chấm đăng ký trước. Không gộp với 12B.
