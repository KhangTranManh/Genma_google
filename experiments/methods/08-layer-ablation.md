# Ba lớp cải tiến độc lập trên 12B và 31B

## Phạm vi

8 lượt smoke mới: 2 model × (đối chứng mới + 3 nhánh). Không có E4B, không
xóa kết quả cũ, không cộng điểm của hai cohort. Mỗi nhánh có experiment ID,
config, state, manifest, prompt snapshot và source snapshot riêng. Đây là lượt
sàng lọc trên URLKit, chưa phải kết luận thống kê hoặc điểm Kaggle.

| Nhánh | Giữ nguyên | Thay đổi duy nhất so với đối chứng |
|---|---|---|
| layers_control_v1 | ProgressAgent detect_only revision 1, recovery prompt, serving | Không đổi; chạy lại đối chứng trên source snapshot chung |
| layers_prompt_v1 | Code revision 1, runtime, task | Prompt completion_contract_v1: checklist review/submit |
| layers_code_v1 | Recovery prompt, runtime, task | Revision 2: nhận diện lệnh test tương đương và giữ lệnh verification trong runtime memory |
| layers_runtime_v1 | Recovery prompt, code revision 1, task, vLLM | Giới hạn lịch sử 12.000 → 18.000 ký tự |

Ba nhánh là độc lập, không cộng dồn prompt+code+runtime. Cấu hình hai model
`focus_12b/focus_31b` trước đây là definition riêng, không được tự chạy/gộp vào đây.

## 1. Prompt

Mục tiêu 12B: sau khi đủ bằng chứng, tự review và gọi submit_patch; xử lý yêu cầu
review của gate bằng lần submit tiếp theo. Mục tiêu 31B: không giảm chất lượng
và giảm vòng kiểm tra thừa nếu có. Checklist không được cho bỏ test hoặc nộp code sai.
Hạn chế: prompt mới không sửa lỗi so khớp test của revision 1; kết quả sẽ phản ánh điều đó.

## 2. Code harness

Phát hiện cụ thể từ run `20261116T071557Z-8c31c62e`: 12B chạy
`python3 -m unittest discover -s tests -v` pass, nhưng verification_command
là `python -m unittest discover -s tests -v`. Revision 1 so khớp chuỗi tuyệt đối
nên không vào review_submit, rồi chặn thao tác lặp và dừng stalled.

Revision 2 cho phép python/python3 và khác verbosity; mọi test target, thư mục,
filter và option khác phải giữ nguyên. Không coi chạy một test con hoặc ghép
shell là verification đầy đủ. Đưa verification_command vào runtime memory để
không bị quên do compact. Không sửa decoder/auto-unescape, không bỏ gate, không
tự nộp patch. Những thay đổi này cùng thuộc một candidate code; chưa tách tác dụng
nhận diện lệnh với runtime memory, không quy riêng toàn bộ gain cho một dòng code.

Lượt kiểm tra vẫn gắn với workspace version. Gate submit chạy lại lệnh cấu hình.

## 3. Project/runtime

Chỉ thử cấu hình lượng lịch sử giữ lại: 18.000 ký tự thay vì 12.000. Mục tiêu là
kiểm tra việc giữ thêm ngữ cảnh có giảm lặp và lỗi tool không. Đo input tokens,
thời gian, số lượt và tỷ lệ tự hoàn tất. Đây là ký tự JSON lịch sử, không phải
18.000 token context. vLLM vẫn max_model_len=8192, max_output_tokens=2048;
HTTP context overflow là lỗi hạ tầng phải ghi nhận và dừng xem lại, không tự tăng
context/chuyển model để che lỗi. Đợt này chưa tối ưu GPU batching hay claim tăng tokens/s.

## Kiểm soát và đánh giá

- Checkpoint pinned, temperature=0, thinking=false, TP=2, task/test/commit cố định.
- 900 giây / 48 lượt / 96 tool requests. Không harness-origin completion ở nhánh nào.
- Chính: model tự submit + toàn bộ test độc lập pass. Public test pass hoặc
  recovered patch pass không được tính thành tự hoàn tất.
- Phụ: solve seconds, input/output tokens, turns/tools, stop reason và nguồn nộp.
- Chấm test độc lập sau khi dừng, không phản hồi ngược cho agent.
- So baseline mới với từng candidate của CÙNG model, không dùng số cũ làm baseline cặp.
- Report kiểm hash controls sau khi bỏ đúng thay đổi dự kiến; sai khác ngoài thiết kế
  sẽ bị cảnh báo. Nhiều thay đổi vô tình không được diễn giải thành gain một yếu tố.
- Mỗi ô có một mẫu nên chỉ kết luận cải thiện/regression trên lượt đó; cần chạy lặp
  và bộ nhiều repo trước khi chọn bản cuối. Không gộp ba nhánh để tính xếp hạng.

## Thực thi và đầu ra

`configs/experiments/layers_{control,prompt,code,runtime}.toml`, mỗi profile chạy
12B rồi 31B. Timer worker thực hiện một phase, study trigger chuyển nhánh sau
khi hoàn tất. Code/prompt/config/dataset đóng băng trước activation; muốn sửa tiếp
phải tạo version/experiment mới. Giữ core bất biến trong suốt đợt chạy.

Bảng mới: `reports/two-model-layers.{md,json,csv}`; tổng hợp HTML:
`reports/study-report.html`. Dữ liệu A/B/C cũ vẫn tách riêng. Khi complete hoặc
needs_review, study timer dừng và lưu snapshot report, gồm HTML.
