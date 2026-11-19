# Lộ trình sau hint ladder (định nghĩa từng bước)

Căn cứ: hint ladder v1/v2 (method 24–25). Với 31B, cần cả cơ chế (A) lẫn hướng sửa (B/G). A+G đạt 4/4 theo bộ chấm nhưng phá ranh giới thẻ. Với 12B, gợi ý và phản hồi dạng văn bản chưa đủ; ở vòng phản hồi, model gửi edit rỗng (old == new).
Nguyên tắc chung: mỗi model là một batch riêng, có state, preflight, hash đầu vào và báo cáo riêng. Không gộp bảng giữa các model. Bộ chấm được chốt trước khi gọi model. Audit sau sự kiện ghi riêng.

Thứ tự: B0 → B1 → (B2 ‖ B3) → B4 → B5 → B6.

---

## B0. Bổ sung bộ chấm "giữ hành vi cũ" (differential oracle)

- **Mục tiêu:** đóng loại lỗ hổng đã gặp hai lần, tức thay đổi ngữ nghĩa mà test hiện có không phủ (thuộc tính dài, `[^<]*` vượt qua `>`).
- **Làm gì:** sinh tự động một corpus input hợp lệ và gần hợp lệ: thẻ đúng, thuộc tính dài, nhiều thẻ, thẻ đã đóng kèm text chứa `href=`, comment, khác hoa/thường. So hàm cũ và hàm mới trên corpus. Yêu cầu khớp 100% trên mọi input mà hàm cũ chạy dưới ngưỡng thời gian. Input bệnh lý (chậm ở hàm cũ) chỉ đo hiệu năng.
- **Preflight:** code gốc khớp chính nó; bản tham chiếu `[^<>]*` khớp 100%; `[^<]*` và `[^> <]*` phải bị bắt.
- **Audit lại:** chấm lại toàn bộ ứng viên lịch sử (v1, v2, các đợt trước) bằng oracle mới. Ghi file audit riêng, không sửa kết quả cũ.
- **Đầu ra:** `scripts/graders/differential.py`, `reports/differential-audit-v1/`.
- **Qua:** preflight phân biệt đúng 4 trường hợp trên. Đây là điều kiện bắt buộc trước B2–B4.

## B1. Chặn lỗi thao tác ngay tại harness

- **Mục tiêu:** không để lượt sửa bị phí vì lỗi cơ học.
- **Làm gì:**
  - (a) Edit có `old_string == new_string`, hoặc không đổi file: không tính là một lượt. Harness trả thông báo ngắn và cho gọi lại đúng 1 lần.
  - (b) Edit đổi ngoài khối được phép: từ chối.
  - (c) Ghi riêng các sự kiện này trong báo cáo.
- **Đo:** số edit rỗng hoặc bị từ chối, và việc gọi lại có tạo ra thay đổi thật hay không.
- **Qua:** có unit test cho cả 3 nhánh. Kiểm thử lại trên quỹ đạo 12B v2 (r1/r2) bằng replay offline.

## B2. 31B — model tự chẩn đoán thay cho A do host viết

- **Mục tiêu:** bỏ phần "host biết đáp án". Đây là điều kiện để harness chạy tự động.
- **Làm gì:**
  1. **Diagnose:** vai riêng, nhận issue, khối source và thời gian công khai của reproducer ở 3 kích thước (2K/4K/8K, cho thấy tốc độ tăng). Output có cấu trúc: `span`, `failing_condition`, `complexity`, `why`. Không có đáp án mẫu trong prompt.
  2. **Patch:** nhận chẩn đoán của chính model và checklist G (giữ nguyên hash v2, không sửa G sau khi đã thấy issue mới).
  3. Python lưu chẩn đoán trước khi Patch. Có thể chấm chẩn đoán offline so với A theo rubric, nhưng điểm này không dùng để chọn ứng viên.
- **Nhánh** (temp 0 và 3 seed mỗi nhánh):

  | Nhánh | Nội dung |
  |---|---|
  | `hostA+G` | Mốc tham chiếu, đã có 4/4 |
  | `selfDiag+G` | Chẩn đoán do model tự viết, kèm G |
  | `selfDiag+G-noTiming` | Như trên nhưng bỏ số liệu thời gian |

- **Chấm:** 4 bộ chấm cũ cộng oracle B0.
- **Qua / dừng:**
  - `selfDiag+G` ≥ 3/4 đạt: chuyển sang B4 với cấu hình này.
  - `selfDiag+G` ≤ 1/4: nút thắt là chẩn đoán. Quay lại tối ưu Diagnose (ví dụ cho model chọn một trong nhiều span có kèm số đo) trước khi mở rộng.

## B3. 12B — harness gánh phần tinh chỉnh (batch riêng)

- **Mục tiêu:** xem 12B có dùng được khi harness lọc thay cho model không.
- **Làm gì:** prompt A+G và A+B+C, temp 0.6, K = 6 mẫu mỗi prompt, có guard B1. Harness lọc theo thứ tự: edit hợp lệ → reproducer công khai → 67 test → oracle B0 công khai trên corpus hợp lệ. Chọn mẫu đầu tiên qua cả bốn. Bộ chấm độc lập chỉ chạy trên mẫu được chọn.
- **Đo:** số mẫu qua từng tầng trên K. Pass@K theo bộ chấm độc lập. Tổng token.
- **Qua / dừng:**
  - Có ≥ 1/6 mẫu qua tất cả ở ít nhất một prompt: giữ 12B làm cấu hình rẻ, dạng chọn mẫu.
  - Không có mẫu nào qua: dừng đầu tư cho 12B ở loại lỗi này.

## B4. Kiểm tra tổng quát trên các issue cùng loại (regex chậm)

- **Mục tiêu:** biết checklist và cấu hình B2/B3 có dùng chung được hay chỉ khớp w3lib_264.
- **Issue ứng viên** (từ `data/freshswe/tasks.jsonl`, chưa dùng trong bất kỳ prompt nào):

  | Issue | Ghi chú |
  |---|---|
  | `w3lib_266` | get_meta_refresh, issue split |
  | `w3lib_268` | replace_tags/remove_tags |
  | `w3lib_271` | remove_tags_with_content |
  | `w3lib_289` | unquote_markup, CDATA chưa đóng |
  | `markdown_1621` | Inline link, lite + issue split. Khác repo, kiểm tra ngoài w3lib |
  | `black_5475` | Bậc hai không do regex. Mở rộng tùy chọn, chủ yếu để xem G có bị áp sai chỗ không |

- **Chuẩn bị cho mỗi issue:**
  1. Snapshot và image Docker.
  2. Reproducer công khai lấy từ chính nội dung issue.
  3. Test chức năng sẵn có.
  4. Bộ chấm độc lập gồm test fail-to-pass của upstream và đo tăng trưởng ở 4 kích thước.
  5. Oracle B0 cho hàm liên quan.
  6. Preflight: code gốc trượt, gold patch đạt.
- **Chống rò rỉ:** chốt hash của G, prompt và cấu hình trước khi đọc chi tiết các issue này. Không chỉnh G theo kết quả của từng issue trong cùng đợt.
- **Chạy:** cấu hình tốt nhất của B2 cho 31B và của B3 cho 12B, mỗi model một batch. Mỗi issue chạy temp 0 và 3 seed.
- **Đo:** số issue đạt trên số issue, theo từng model. Phân loại lỗi: chẩn đoán sai span, sửa sai lớp ký tự, phá ngữ nghĩa, lỗi tool.
- **Qua:** 31B đạt ≥ 3/5 issue regex. Khi đó mới coi "chẩn đoán + checklist theo loại lỗi" là hướng chính.

## B5. Mở rộng sang loại lỗi khác

- **Mục tiêu:** xem cách "checklist theo loại lỗi" có nhân rộng được không.
- **Làm gì:** chọn 1–2 loại lỗi phổ biến trong pool, ví dụ thiếu validate input hoặc edge-case (`platformdirs_540`, `packaging_1230`, `packaging_1305`, `werkzeug_3147`). Viết một checklist cho mỗi loại, chốt trước. Thêm bước phân loại issue (model chọn loại lỗi) để chọn checklist.
- **Đo:** độ chính xác phân loại; tỷ lệ đạt so với không có checklist, trên cùng issue và cùng model.
- **Qua:** checklist cải thiện so với đối chứng trên ≥ 2 issue mỗi loại.

## B6. Đưa vào pipeline chính thức

- **Làm gì:** gộp guard B1, Diagnose → Patch có checklist, oracle B0 (bản công khai) vào runtime khai báo chính thức. Chạy lại pilot 3 issue và các issue của B4.
- **Kaggle:** chỉ nộp khi người dùng xác nhận.

---

**Chi phí ước tính:**

| Bước | Lượt gọi model |
|---|---|
| B0, B1 | Không gọi model |
| B2 | ~24 lượt (31B) |
| B3 | ~12 lượt (12B) |
| B4 | ~5 issue × 4 lượt × 2 model, cộng công chuẩn bị bộ chấm cho mỗi issue. Đây là phần tốn công nhất |

**Rủi ro đã biết:**
- G được viết sau khi đã thấy w3lib_264.
- Các issue w3lib cùng tác giả và cùng phong cách regex, nên cần `markdown_1621` để kiểm tra ngoài repo.
- 3 seed mỗi nhánh chỉ là kiểm tra độ ổn định, chưa phải tỷ lệ.

---

## Trạng thái (2026-11-18)

- **B0 xong.** Oracle `scripts/graders/w3lib_264_differential.py` dùng được (preflight đạt). Audit 161 ứng viên: chỉ `[^<>]*` đạt. **31B A+G từ 4/4 xuống 0/4** (`[^<]*` vượt qua `>`). 31B A+B vẫn đạt 3/4 (v1 temp 0, v2 seed 17 và 43). Chi tiết ở `reports/differential-audit-v1/analysis.md`.
- **B1 xong.** `scripts/harness/edit_guard.py`, 8/8 unit test đạt. Replay offline cho thấy guard bắt được 6/71 lượt từng mất vì lỗi cơ học. Chi tiết ở `reports/edit-guard-replay-v1/analysis.md`.
- **Ảnh hưởng đến B2:** mốc so sánh `hostA+G` không còn đạt. Theo oracle mới, checklist G chung chỉ đưa 31B tới gần đúng (`[^<]*`), chưa tới đúng (`[^<>]*`). Muốn đạt phải dùng B (viết khi đã biết đáp án) hoặc một G được sửa lại. G sửa lại phải chốt trước và chỉ được kiểm chứng trên issue mới (B4), không phải trên w3lib_264.
- **B2 xong** (`reports/b2-selfdiag-v1/31b/analysis.md`). Tự chẩn đoán đúng 4/4. selfdiag+G đạt 1/4 (`[^<>]*`), hostA+G đạt 0/4. Phản hồi differential kéo `[^<]*?` về `[^>]*?` thay vì `[^<>]*`. Có thêm lỗi lặp call no-op đến khi bị cắt; guard cần luật mới.
- **B3 xong** (`reports/b3-sampling-v1/12b/analysis.md`). Theo bộ chấm, A+B+C đạt 1/6 (`[^>\[<]*`, harness chọn đúng); A+G đạt 0/6. Audit sau sự kiện cho thấy `[` bị loại nhầm, corpus differential bỏ sót, nên thực tế 0/12.
- **Việc trước B4:** (1) mở rộng corpus differential ra mọi ký tự ASCII in được trong giá trị thuộc tính, preflight phải bắt được `[^>\[<]*`; (2) guard coi nhiều call giống hệt nhau là no-op; (3) cân nhắc dùng lấy mẫu + lọc công khai làm chiến lược Patch mặc định cho 31B.
- **Oracle v2 + guard nâng cấp xong** (`reports/differential-audit-v2/`). Corpus phủ mọi ký tự ASCII in được. Guard gộp call trùng, bỏ call bị cắt, và có `check_edits` cho nhiều vùng (15 test).
- **B4 đợt 1 xong** (`reports/b4-v1/<model>/analysis.md`, method 28). 31B giải được 1/3 bài: w3lib_266 4/4 mẫu. 268 thì chỉ sửa 1/2 vùng; 271 rơi về lazy. 12B đạt 0/3 bài, 0/18 mẫu. Chưa đạt ngưỡng "≥3/5 bài" của roadmap.
- **Đề xuất tiếp:**
  1. Public check theo từng hàm được nêu trong issue, để bắt trường hợp sửa thiếu vùng.
  2. Lấy mẫu thích nghi: lấy thêm khi chưa có mẫu qua public, có trần ngân sách.
  3. Dừng 12B cho loại lỗi này.
  4. Đợt 2 (w3lib_289, markdown_1621) chỉ chạy sau khi có (1) và (2).
- **B4 v2 xong** (`reports/b4-v2/31b/analysis.md`, method 29). Vẫn 1/3 bài.
  - 268: 16 lượt không lượt nào sửa `_tags_re`.
  - 271: harness chọn `[^<]*`. Mẫu này qua public nhưng hidden differential lệch 2 ca có `>` trong giá trị thuộc tính có nháy.
  - Việc tiếp theo:
    1. Tách Patch theo từng vùng, mỗi vùng gắn với hàm chậm của nó.
    2. Đưa ca `>` trong giá trị có nháy vào public corpus (preflight: upstream lệch 0 ca).
- **B4 v3 xong** (`reports/b4-v3/31b/analysis.md`, method 30). Vẫn 1/3 bài.
  - Patch theo vùng làm 31B sửa được `_tags_re`: 3/6 mẫu làm cả hai hàm nhanh. Nhưng nó viết lại tên thẻ nên lệch hành vi.
  - Corpus v2 chặn được `[^<]*` ngay ở bước public.
  - Kết luận: harness đã làm tốt phần chọn mẫu; phần còn thiếu là kiến thức sửa của model.
  - Hướng tiếp theo, cần chọn một: (a) gợi ý sửa cụ thể theo loại lỗi, phải kiểm chứng trên bài mới; (b) chuyển sang B5 với loại lỗi khác.
