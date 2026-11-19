# So sánh kết hợp code + prompt: 12B và 31B

Đối chứng code revision 2 + recovery prompt so với code revision 2 + completion prompt. Tất cả dùng model tự submit, không bật harness nộp hộ.

| Model | Nhánh | Kết quả | Tự submit + pass | Giây | Lượt | Tools |
|---|---|---|---|---:|---:|---:|
| 12b | Code mới + prompt cũ | local_pass | True | 109.01 | 16 | 16 |
| 12b | Code mới + prompt mới | local_pass | True | 102.178 | 14 | 14 |
| 31b | Code mới + prompt cũ | local_pass | True | 136.543 | 12 | 12 |
| 31b | Code mới + prompt mới | local_pass | True | 214.338 | 17 | 17 |

URLKit tạo commit mới mỗi lượt (timestamp khác). So khớp nội dung bằng dataset hash đã đóng băng; giữ SHA gốc trong từng record. Repo thực vẫn so SHA chính xác.

## Đánh giá theo cặp

- 12b / Code mới + prompt mới: Cả hai tự submit và pass; thời gian candidate trừ baseline = -6.8s. Một mẫu chưa chứng minh cải thiện ổn định.
- 31b / Code mới + prompt mới: Cả hai tự submit và pass; thời gian candidate trừ baseline = +77.8s. Một mẫu chưa chứng minh cải thiện ổn định.

## Bằng chứng

- [20261116T095110Z-1b568551](../runs/20261116T095110Z-1b568551/manifest.json)
- [20261116T095508Z-17560357](../runs/20261116T095508Z-17560357/manifest.json)
- [20261116T100127Z-9d8867f5](../runs/20261116T100127Z-9d8867f5/manifest.json)
- [20261116T100516Z-7145d893](../runs/20261116T100516Z-7145d893/manifest.json)

## Kiểm tra thiết kế

Chưa phát hiện sai khác ngoài thiết kế.
