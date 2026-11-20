# Ba bước sau v6 — kế hoạch và nơi lưu kết quả

Các batch dùng GPU chạy tuần tự qua `scripts/generic/queue_steps.sh` (tách khỏi phiên làm việc; log `runs/generic-queue.log`).

| Bước | Nội dung | Kết quả lưu ở |
|---|---|---|
| 1. Độ dao động | Chạy lặp 2 lần cấu hình v5 (`--evidence --extra-checks`) trên 8 bài dev: `generic-rep1`, `generic-rep2`. Cộng với v5 (và vòng 0 của v6) để đo phạm vi | `reports/generic-rep1/`, `reports/generic-rep2/`, tổng hợp `reports/generic-steps/step1-variance.md` |
| 2. Mở rộng tập dev | 12 bài mới theo quy tắc cố định (`experiments/generic_v1/dev20-tasks.json`), tải snapshot, dựng image, preflight chính thức; bài không qua preflight bị loại kèm lý do. Chạy pipeline trên các bài dùng được: `generic-dev20` | `runs/generic-preflight-v1/`, `reports/generic-dev20/`, tổng hợp `reports/generic-steps/step2-dev20.md` |
| 3. Bài nộp chính thức | `submission_candidates/generic_v1/31b`: SequentialAgent reproduce → localize (cProfile/traceback) → checks (fixed_/preserve_) → LoopAgent(editor, verifier)×2 → submit. Compile bằng thư viện chính thức đạt. Chạy Evaluator chính thức trên 8 bài dev | `runs/official-generic-v1/31b/summary.json`, tổng hợp `reports/generic-steps/step3-official.md` |

Ràng buộc của bài nộp chính thức: chỉ YAML + prompt, không callback tự viết, không code Python điều phối; giới hạn 15 phút, 48 lượt, 96 tool call mỗi bài. Các cổng kiểm tra cứng và việc chọn mẫu của harness Python không mang sang được; chúng được chuyển thành chỉ dẫn trong prompt cho agent tự chạy lệnh.

Đã loại ở bước 2 (preflight): `black_5476` — bản sửa gốc cũng không resolved trong môi trường này.

## Pilot QLoRA 12B

[Huấn luyện và đánh giá LoRA](step4-lora.md) đã hoàn tất. 12B + LoRA và 12B gốc cùng giải đúng 1/8 bài dev.
