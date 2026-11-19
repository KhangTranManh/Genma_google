# So sánh chống loop trên ba model

Giữ cùng system prompt, issue, test độc lập, vLLM và giới hạn 900 giây / 48 lượt / 96 thao tác.
A dùng AgentLoop cũ. B thêm trạng thái và phát hiện lặp. C thêm xác minh và bước nộp do harness điều phối.

## Trạng thái từng phần

- A: đối chứng: **complete**.
- B: chống lặp: **complete**.
- C: chốt có xác minh: **complete**.

| Model | Cấu hình | Kết quả | Test độc lập | Giây | Lượt / tools | Output tokens | Lặp bị chặn | Nguồn nộp | Patch thu hồi |
|---|---|---|---|---:|---|---:|---:|---|---|
| e4b | A: đối chứng | incomplete | - | 523.4 | 48 / 41 | 29997 | 0 | - | fail / lỗi |
| e4b | B: chống lặp | incomplete | - | 618.3 | 48 / 44 | 35579 | 0 | - | fail / lỗi |
| e4b | C: chốt có xác minh | incomplete | - | 502.2 | 48 / 48 | 27613 | 0 | - | fail / lỗi |
| 12b | A: đối chứng | incomplete | - | 229.7 | 48 / 48 | 3580 | 0 | - | pass (chỉ chẩn đoán) |
| 12b | B: chống lặp | incomplete | - | 102.2 | 17 / 17 | 1805 | 4 | - | pass (chỉ chẩn đoán) |
| 12b | C: chốt có xác minh | local_pass | 6/6 | 69.4 | 8 / 8 | 1543 | 0 | harness | - |
| 31b | A: đối chứng | incomplete | - | 344.7 | 48 / 48 | 2125 | 0 | - | fail / lỗi |
| 31b | B: chống lặp | local_pass | 6/6 | 219.0 | 18 / 18 | 1821 | 0 | model | - |
| 31b | C: chốt có xác minh | local_pass | 6/6 | 195.1 | 15 / 15 | 1775 | 0 | harness | - |

## Quy ước

- `model`: model gọi submit_patch; `harness`: bộ điều phối chốt sau kiểm tra trên đúng code version.
- Patch thu hồi được chấm riêng sau khi dừng, không tính thành nộp patch thành công.
- Test độc lập chỉ chạy sau khi kết thúc và không được đưa lại cho agent.
- Code đổi sẽ vô hiệu hóa kết quả test cũ. Lượt test đã pass không được dùng cho code version mới.
- Thời gian task gồm quan sát trạng thái và kiểm tra của harness; không dùng thời gian chấm patch thu hồi để đánh giá hiệu suất agent.
- C là chế độ hỗ trợ nộp của harness local, chưa chứng minh model tự nộp được trong runtime chính thức.
- Một issue mỗi cấu hình là thử nghiệm tích hợp, chưa đủ kết luận hiệu quả trên repo thực tế.

## Bằng chứng

- 31b / A: đối chứng: [manifest](../runs/20261116T064438Z-a5dae13e/manifest.json)
- 12b / A: đối chứng: [manifest](../runs/20261116T065237Z-2f2f1f79/manifest.json)
- e4b / A: đối chứng: [manifest](../runs/20261116T065837Z-c3cb7105/manifest.json)
- 31b / B: chống lặp: [manifest](../runs/20261116T070957Z-325fe24c/manifest.json)
- 12b / B: chống lặp: [manifest](../runs/20261116T071557Z-8c31c62e/manifest.json)
- e4b / B: chống lặp: [manifest](../runs/20261116T071942Z-c13011dd/manifest.json)
- 31b / C: chốt có xác minh: [manifest](../runs/20261116T073405Z-5be811c3/manifest.json)
- 12b / C: chốt có xác minh: [manifest](../runs/20261116T073927Z-cd0ec631/manifest.json)
- e4b / C: chốt có xác minh: [manifest](../runs/20261116T074230Z-722f1299/manifest.json)
