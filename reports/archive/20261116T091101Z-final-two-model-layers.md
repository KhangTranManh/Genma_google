# So sánh từng lớp: 12B và 31B

Đối chứng mới + ba nhánh độc lập. Tất cả dùng model tự submit, không bật harness nộp hộ.

| Model | Nhánh | Kết quả | Tự submit + pass | Giây | Lượt | Tools |
|---|---|---|---|---:|---:|---:|
| 12b | Đối chứng B | incomplete | False | 102.155 | 17 | 17 |
| 12b | 1 · Prompt | local_pass | True | 154.288 | 15 | 14 |
| 12b | 2 · Code harness | local_pass | True | 109.013 | 16 | 16 |
| 12b | 3 · Context runtime | incomplete | False | 183.261 | 17 | 16 |
| 31b | Đối chứng B | local_pass | True | 218.911 | 18 | 18 |
| 31b | 1 · Prompt | local_pass | True | 144.785 | 12 | 12 |
| 31b | 2 · Code harness | local_pass | True | 136.524 | 12 | 12 |
| 31b | 3 · Context runtime | local_pass | True | 188.949 | 14 | 14 |

URLKit tạo commit mới mỗi lượt (timestamp khác). So khớp nội dung bằng dataset hash đã đóng băng; giữ SHA gốc trong từng record. Repo thực vẫn so SHA chính xác.

## Đánh giá theo cặp

- 12b / 1 · Prompt: Cải thiện tự hoàn tất trên lượt này; cần chạy lặp để xác nhận.
- 12b / 2 · Code harness: Cải thiện tự hoàn tất trên lượt này; cần chạy lặp để xác nhận.
- 12b / 3 · Context runtime: Chưa cải thiện tự hoàn tất trong cặp này; xem patch thu hồi và trajectory.
- 31b / 1 · Prompt: Cả hai tự submit và pass; thời gian candidate trừ baseline = -74.1s. Một mẫu chưa chứng minh cải thiện ổn định.
- 31b / 2 · Code harness: Cả hai tự submit và pass; thời gian candidate trừ baseline = -82.4s. Một mẫu chưa chứng minh cải thiện ổn định.
- 31b / 3 · Context runtime: Cả hai tự submit và pass; thời gian candidate trừ baseline = -30.0s. Một mẫu chưa chứng minh cải thiện ổn định.

## Bằng chứng

- [20261116T081014Z-cda35fd0](../runs/20261116T081014Z-cda35fd0/manifest.json)
- [20261116T081403Z-38ed1f10](../runs/20261116T081403Z-38ed1f10/manifest.json)
- [20261116T082234Z-4e2eecd8](../runs/20261116T082234Z-4e2eecd8/manifest.json)
- [20261116T082726Z-7b29fe29](../runs/20261116T082726Z-7b29fe29/manifest.json)
- [20261116T083442Z-27293526](../runs/20261116T083442Z-27293526/manifest.json)
- [20261116T083839Z-b5e0a98a](../runs/20261116T083839Z-b5e0a98a/manifest.json)
- [20261116T084445Z-865bc7cc](../runs/20261116T084445Z-865bc7cc/manifest.json)
- [20261116T084957Z-ed7f1600](../runs/20261116T084957Z-ed7f1600/manifest.json)

## Kiểm tra thiết kế

Chưa phát hiện sai khác ngoài thiết kế.
