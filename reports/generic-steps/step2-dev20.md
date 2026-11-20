# Bước 2 — Mở rộng tập dev (9 bài mới, 9 repo mới; 31B, cấu hình v5)

Chọn 12 bài theo quy tắc cố định (`experiments/generic_v1/dev20-tasks.json`). Preflight chính thức loại 3 bài:

- `black_5476`: gold patch không resolved trong môi trường này
- `isort_2558`: gold patch không resolved
- `isort_2581`: gold patch không resolved

| Bài | Khoanh đúng file | Repro | Harness chọn | Chấm chính thức | Có mẫu đúng | Ghi chú |
|---|---|---|---|---|---|---|
| flask_6133 | ✗ | ✓ | — | — | ✗ | khoanh sai file; bằng chứng profiler toàn thời gian import |
| litestar_4659 | ✗ | ✓ | — | — | ✗ | khoanh sai file; bằng chứng profiler toàn thời gian import |
| loguru_1504 | ✓ | ✓ | t0 | — | ✗ | chọn sai: qua public, trượt test ẩn |
| more_itertools_1285 | ✓ | ✓ | — | — | ✗ | khoanh đúng, không mẫu nào qua public, không mẫu nào đúng |
| pluggy_752 | ✓ | ✓ | — | — | ✓ | **4/4 mẫu đúng nhưng bị loại oan**: repro và ca fixed_* tự gọi sai API (TypeError trong script) |
| typer_1788 | ✗ | ✓ | — | — | ✗ | khoanh sai file; không thu được bằng chứng |
| urllib3_5031 | ✓ | ✓ | — | — | ✗ | khoanh đúng, không mẫu nào đúng |
| uvicorn_3199 | ✓ | ✓ | t0 | resolved | ✓ | **giải được** |
| click_3739 | ✓ | ✓ | — | — | ✓ | **4/4 mẫu đúng nhưng bị loại oan**: repro tự bắt TypeError do chính nó dùng sai API |

**Chọn đúng: 1/9. Có mẫu đúng: 3/9. Khoanh đúng file: 6/9. Chọn sai: 1/9.**

Gộp với 8 bài dev cũ (rep2): chọn đúng **3/17** (w3lib, click_3299, uvicorn). Riêng các bài mới thấp hơn nhiều so với tập 8 bài (2/8), nên tập 8 bài ban đầu đã lạc quan.

## Phát hiện

1. **Có 2 bài bị loại oan dù 4/4 mẫu đúng** (pluggy, click_3739). Repro hoặc ca `fixed_*` do model viết tự trượt vì chính nó gọi sai API. Nếu sửa được lỗi này, kết quả lên 3/9.
2. **Khoanh vùng yếu với lỗi logic** (flask, litestar, typer). Profiler chỉ thấy thời gian import; nó hữu ích với lỗi hiệu năng (markdown), không phải lỗi sai kết quả.

## Đã sửa ở v7 (cờ `--v7`, áp dụng chung)

- **Repro:** không tính là hợp lệ nếu traceback cho thấy exception (khác AssertionError) phát sinh ngay trong script. Prompt yêu cầu không tự bắt exception và đối chiếu chữ ký hàm trong source. Kiểm tra trên dữ liệu cũ: 15/16 repro hợp lệ vẫn đạt, chỉ repro sai của pluggy bị loại.
- **Ca `fixed_*`:** bỏ ca trượt vì exception không phải AssertionError phát sinh ngay trong module kiểm tra.
- **Bằng chứng:** loại `<module>`; thêm danh sách hàm của repo được gọi khi chạy repro. Với flask, danh sách này có đúng file của bản sửa gốc (`sansio/scaffold.py`).

Chưa xử lý: repro tự bắt exception rồi `exit 1` mà không in traceback (click_3739). Quy tắc "bắt buộc có traceback" sẽ loại oan 12/16 repro hợp lệ nên đã bỏ; v7 chỉ thêm yêu cầu này vào prompt.
