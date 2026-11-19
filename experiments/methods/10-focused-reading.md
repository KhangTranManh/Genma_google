# Định nghĩa: đọc repo có mục tiêu trên 12B và 31B

Trạng thái: đã định nghĩa và tạo candidate để kiểm tra compiler. Chưa chạy model,
chưa bật trigger, chưa khẳng định có cải thiện.

## Vấn đề từ pilot

31B có 43 read_file requests ở w3lib, 39 ở packaging và 37 ở platformdirs trong
ngân sách 48 lượt. Đây là request ghi trong trajectory, gồm thao tác cuối có thể
bị budget từ chối; không đồng nghĩa mọi read đều đã thực thi hoặc đều vô ích.
Có trường hợp filepath bị nối `start_line` vào trong chuỗi. Cả hai model đạt 0/3
issue; số lần đọc cao chỉ là triệu chứng, chưa chứng minh nguyên nhân duy nhất.

## Ba nhánh tách riêng

| Nhánh | Nội dung | Cặp so sánh |
|---|---|---|
| R0 baseline | Recovery prompt, 6 tools chính thức, không skill | Đối chứng chạy mới |
| R1 prompt | R0 + quy trình tìm → đọc phạm vi → checkpoint → hành động | R1 so R0: hiệu quả gói hướng dẫn đọc |
| R2 skill | R1 + ADK skill focused-repo-reading và hướng dẫn load | R2 so R1: hiệu quả bổ sung skill/toolset và lời nhắc load |

R2 thay cả khả năng load skill lẫn instruction gọi skill: báo cáo là một candidate
skill, không quy riêng gain cho nội dung tài liệu. Không gộp R1/R2 thành một phương pháp.
Không thay source runtime, không custom host callback, không auto-submit hay cưỡng
chế giới hạn đọc bằng code Python local. Không subagent ở đợt này.

## Quy trình đọc được thử

1. Mỗi lần đọc trả lời một câu hỏi cụ thể: vị trí hành vi, contract của caller,
   hoặc test đang bao phủ điều gì.
2. Tìm symbol/path bằng search có phạm vi. Dùng rg nếu có, git grep nếu không;
   không cài dependency hoặc dump toàn repo.
3. Đọc khoảng 60–120 dòng quanh định nghĩa, tuân thủ giới hạn tool; dùng filepath,
   start_line, end_line thành các trường JSON riêng, bounds kiểu số nguyên.
4. Sau bốn thao tác inspection, checkpoint ngắn: yêu cầu, bằng chứng, giả thuyết,
   việc tiếp theo. Đây là nhắc nhở mềm; được đọc thêm khi chỉ rõ điều chưa biết.
5. Chuyển sang reproduce/edit/test khi đủ thông tin. Đọc lại khi file đổi, lỗi mới
   hoặc giả thuyết thay đổi; output bị cắt thì chỉ đọc phần thiếu.
6. Ghi nhớ ngắn trong conversation, không tạo file note gây bẩn patch. Kiểm tra,
   review và model tự submit. Không đoán code hoặc bỏ test chỉ để giảm số lần đọc.

## Thiết kế đo

18 lượt development: 2 model × 3 nhánh × 3 issue pilot đã xem. Cần baseline mới
trong cùng đợt; không coi số pilot cũ là cặp baseline duy nhất. Cùng checkpoint,
serving, image, snapshot, prompt gốc, context và compaction. 48 lượt / 96 tool
requests / 15 phút, temperature=0, thinking=0. Một lượt/ô chưa đủ kết luận ổn định.
Cấu hình máy local 2 A16, vLLM 0.33.0 và context8192 khác môi trường scorer.

**Chính:** model gọi submit_patch thành công và test độc lập pass. Phân biệt
explicit submission với patch fallback thu khi hết budget. Resolved test nhưng
không submit được báo riêng. Không dùng trường `status=SUCCESS` của runner làm
bằng chứng sửa issue thành công; cần `resolved`, patch và dấu submit trong trace.

**Phụ:** request read_file và lỗi arguments; đọc lại cùng filepath/range khi nội
dung trả về không đổi; khoảng mở rộng/overlap; lượt tới implementation edit đầu;
turns/tools, tokens, thời gian, nguyên nhân dừng; skill có được load/resource nào
được mở. Có read nhiều nhưng hợp lý thì không tính là lỗi chỉ dựa vào count.
Dữ liệu thiếu phải ghi là missing, không tự điền 0.

Giảm đọc nhưng patch sai không được coi là cải thiện. Với patch pass ngang nhau,
xem hiệu suất và biến thiên trước khi chọn. Nếu candidate làm mất pass thì chưa
promote. Chưa đặt ngưỡng phần trăm tùy ý từ ba issue đã xem.

## Không rò rỉ và xác nhận sau development

Không đưa gold patch/test_patch hoặc test chấm độc lập vào prompt/skill/context.
Không nêu lời giải của ba issue cụ thể trong protocol. Task/snapshot/reference
chỉ ở phía evaluator đáng tin. Đã nhìn pilot nên ba issue này chỉ là development,
không phải holdout, không dùng chúng để ước lượng khả năng vượt leaderboard 0.29.

Sau development, đóng băng candidate và chọn trước tập issue chưa xem từ nhiều
repo, chạy lặp và ghi cặp thắng/thua/hòa. Chưa chuẩn bị/chạy tập holdout ở bước define.

## Artifact

- Plan: configs/reading-study.toml.
- Builder: scripts/official/build_reading_candidates.py.
- Candidates: submission_candidates/reading_v1/{baseline,prompt,skill}/{12b,31b}/.
- Prompt: experiments/prompts/focused_reading_v1.md.
- ADK skill: experiments/skills/focused-repo-reading/.
- Compiler validation và ZIP lưu riêng trong reports/reading-v1/ và dist/reading-v1/.

Baseline pilot, gói submission cũ và kết quả cũ giữ nguyên. Chỉ compiler validation
ở bước này; chưa tạo runtime job hay đăng ký timer cho 18 lượt.

## Thực thi và quan sát (đã bổ sung)

Hàng đợi 18 cell nằm ở scripts/official/reading_worker.py. Mỗi model chạy lần lượt
ba issue; với mỗi issue, thứ tự cố định là R1 → R0 → R2 để quan sát protocol mới
sớm. Thứ tự không được randomize; không diễn giải chênh lệch thời gian một mẫu
thành kết luận thống kê. Giữ riêng trạng thái dưới runs/reading-v1/ và không sửa
pilot cũ. Candidate prompt/config/runtime/task/ảnh Docker được đóng băng trước chạy.

Mỗi lượt lưu submission snapshot, run-inputs.json, kết quả evaluator, patch, ATIF
trace và reading-metrics.json. Chỉ đánh dấu autonomous_pass khi resolved=true và
quan sát được submit_patch thành công với patch không rỗng. Fallback patch không
được coi là model tự nộp. Skill activation được xác nhận từ tool result, không chỉ
vì YAML có trường skills.

Timer worker tiến một job mỗi lần. Watch timer đọc log mỗi phút, ghi live.json và
observations.jsonl; cảnh báo khi có tám read_file liên tiếp hoặc log im quá 300 giây.
Đây là cảnh báo thụ động để xem xét, không tự nhắc/chặn/đổi model giữa lượt. Log
chỉ là quan sát tạm thời; phân tích đầy đủ dựa trên ATIF sau kết thúc.

Nguồn metric có giới hạn: timing sửa chỉ đo edit_file/write_file source thành công,
không bao gồm sửa bằng shell; tổng token cộng từ agent-step metrics, không phải
billing; đọc lặp cùng nội dung chưa đủ chứng minh vô ích. Dữ liệu thiếu để null.

Nếu job bị ngắt, input đổi, hoặc lỗi runtime rõ như model endpoint/context overflow,
queue dừng needs_review để điều tra; không tự sửa source rồi trộn kết quả cũ. Timer
dừng khi complete/needs_review. Xem báo cáo thực thi reports/reading-v1/comparison.html.
