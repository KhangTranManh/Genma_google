# Official-runtime integration and independent pilot

Updated: 2026-11-18T08:12:59.253895+00:00

State: complete

Official public wheelhouse v31 compiler/evaluator with independent FreshSWE-Py tasks; not Kaggle competition score.

## Compiler / package validation

| Model | Valid directory | Compiled | Kaggle scored |
|---|---|---|---|
| 12b | True | True | False |
| 31b | True | True | False |

## Environment calibration

| Task | Original fails | Reference passes | Usable |
|---|---|---|---|
| w3lib_264 | True | True | True |
| packaging_1125 | True | True | True |
| platformdirs_540 | True | True | True |

## Agent evaluation

| Model | Task | Result | Seconds | Tools |
|---|---|---|---:|---:|
| 12b | w3lib_264 | fail | 406.0007119360016 | 46 |
| 12b | packaging_1125 | fail | 308.4468853419967 | 47 |
| 12b | platformdirs_540 | fail | 148.07064771799924 | 14 |
| 31b | w3lib_264 | fail | 722.828594259001 | 47 |
| 31b | packaging_1125 | fail | 567.4916919149982 | 47 |
| 31b | platformdirs_540 | fail | 732.4122517169963 | 47 |

## Phân tích sau pilot

- Đã kết thúc 6/6 lượt; thành công 0 lượt. Đây là pilot ba issue/model, không phải ước lượng điểm leaderboard.
- 5/6 lượt chạm giới hạn 48 lượt. Thời gian ngắn hơn 900 giây không có nghĩa còn lượt để thử tiếp.
- w3lib: patch của cả hai model chưa xử lý được test hiệu năng về catastrophic backtracking; chấm độc lập ghi 67 pass / 1 fail. packaging: cả hai không có patch thu hồi, nên không ghi 0 test pass như một kết quả đã chạy test.
- Các request read_file chiếm phần lớn lượt ở 31B; một số filepath bị ghép sai với start_line. Đây là triệu chứng từ trajectory, chưa chứng minh do model, prompt hay parser riêng lẻ.
- ProgressAgent và bộ chặn loop local không chạy trong pilot này. Không thể chuyển kết luận pass ở URLKit sang runtime chính thức hoặc quy toàn bộ khác biệt cho model.
- Ưu tiên tiếp: phân loại lỗi tool/đọc lặp/patch rỗng; thử prompt ví dụ arguments chính xác và hạn mức đọc trước khi sửa bằng YAML/prompt/skills được hỗ trợ. Giữ đối chứng, không tăng lượt để che loop; cần thêm issue trước khi kết luận năng lực tổng quát.

## Differences from scored Kaggle runtime

- 2 A16 GPUs / vLLM 0.33.0 / 8192 context, not official 4 L4 / wheelhouse vLLM / 32768 context
- Host dependencies resolved locally; organizer core wheels and ADK version pinned, not a full wheelhouse recreation
- Local ProgressAgent and its verification fix are not used by the official runtime
- Three public issue-sourced tasks selected before model outcomes; not a representative score estimate

Competition tasks/snapshots endpoint returned HTTP 401 without authentication. No login or competition submission performed.

Sources: [organizer wheelhouse](https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse), [organizer starter](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent), [independent dataset](https://www.kaggle.com/datasets/moshegolderson/freshswe-py).
