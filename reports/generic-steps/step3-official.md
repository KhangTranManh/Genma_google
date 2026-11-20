# Bước 3 — Bài nộp chính thức (ADK YAML + prompt), đánh giá bằng Evaluator chính thức (31B, 8 bài dev)

Ràng buộc: chỉ YAML + prompt, không callback tự viết, không điều phối Python; mỗi bài tối đa 15 phút, 48 lượt, 96 tool call. Số trong ngoặc là số lượt gọi model.

| Bài | v1 | v2 | v3 | v4 | v5 | v6 | Python pipeline (rep2) |
|---|---|---|---|---|---|---|---|
| w3lib_264 | ✗ hết 15 phút (25) | ✗ hết 15 phút (41) | ✗ hết 15 phút (32) | ✗ hết lượt (48) | **✓** (19) | ✗ hết lượt (48) | ✓ |
| markdown_1621 | ✗ hết lượt (48) | — | — | — | ✗ hết lượt (48) | ✗ nộp sai (27) | ✗ |
| werkzeug_3147 | — | — | — | — | ✗ hết lượt (48) | ✗ nộp sai (38) | ✗ |
| tenacity_640 | — | — | — | — | ✗ hết lượt (48) | ✗ hết lượt (48) | ✗ |
| humanize_334 | — | — | — | — | ✗ nộp sai (31) | ✗ nộp sai (26) | ✗ |
| packaging_1155 | — | — | — | — | ✗ nộp sai (12) | ✗ nộp sai (14) | ✗ |
| click_3299 | — | — | — | — | **✓** (20) | **✓** (20) | ✓ |
| platformdirs_540 | — | — | — | — | ✗ nộp sai (34) | ✗ nộp sai (35) | ✗ |
| **Resolved** | **0/2** | **0/1** | **0/1** | **0/1** | **2/8** | **1/8** | **2/8** |

## Các phiên bản và lỗi tìm ra

| Bản | Cấu trúc | Lỗi chặn |
|---|---|---|
| v1 | 7 agent: reproduce, localize, checks, loop(editor, verifier)×2, submit | Quá nhiều bước: hết 15 phút hoặc hết 48 lượt trước khi sửa |
| v2 | Gộp investigate, bỏ checks, giới hạn tool call trong prompt | **Model bỏ qua giới hạn trong prompt** (41 lượt viết lại repro); đường dẫn file bị dính dấu backtick |
| v3 | Agent hẹp 1–2 tool, lệnh cố định chép sẵn | **Tham số số bị biến dạng ở tầng tool**: `read_file(start_line=151)` tới tool thành `start_line"`, nên luôn trả về dòng 1–150; lặp 32 lần |
| v4 | Xem code bằng `run_command` (sed/grep), không dùng tham số số | **Dấu `\` trước dấu nháy bị mất**: `[\"\']` tới tool thành `[\"']`, nên `edit_file` không khớp; model viết đúng bản sửa nhưng thất bại hơn 30 lần |
| **v5** | v4 + `old_string` ngắn nhất, tránh dấu nháy và `\`, rút ngắn khi không tìm thấy | **2/8 resolved**, ngang pipeline Python. Còn lại: editor có cả quyền xem lẫn sửa, nên ở 3 bài chỉ xem mà không sửa, hết 48 lượt |
| v6 | v5 + tách viewer / editor chỉ có `edit_file` / verifier | Hết kẹt ở bước xem (markdown, werkzeug đã nộp được patch), nhưng editor không theo chỉ dẫn "đoạn ngắn" và không xem lại được, nên lặp lỗi escape ở w3lib; 1/8 |

## Kết luận

- **Bài nộp chính thức tốt nhất hiện tại: `submission_candidates/generic_v5/31b` (2/8)**, bằng pipeline Python trên cùng 8 bài (2/8; trung bình 2,25/8 qua 4 lần chạy). Hai bài giải được giống nhau (w3lib, click).
- Lỗi chặn chính ở đường gọi chính thức nằm ở **tầng tool call** (Gemma qua LiteLLM/ADK): tham số số bị biến dạng, mất `\` trước dấu nháy. Không lỗi nào xuất hiện ở pipeline Python, vốn gọi API vLLM trực tiếp. Đây nhiều khả năng là một nguyên nhân khiến các đợt agent chính thức trước đây (pilot, staged, simple) đều 0 điểm.
- **Ràng buộc thiết kế:** giới hạn trong prompt không có tác dụng, chỉ cấu trúc (tool được cấp, chuỗi agent, LoopAgent) mới kiểm soát được hành vi. Agent có cả quyền xem lẫn sửa dễ kẹt ở bước xem; agent chỉ có quyền sửa thì không tự sửa lỗi escape được.

## Đề xuất tiếp

1. Giữ v5 làm bài nộp hiện tại.
2. v7: giữ editor có quyền xem (như v5), nhưng tách mỗi vòng thành viewer (1 lệnh) rồi editor (xem + sửa) trong `LoopAgent` nhiều vòng ngắn, để giảm kẹt mà vẫn tự sửa được lỗi escape.
3. Chạy lại v5 1–2 lần để đo dao động trên đường chính thức.
