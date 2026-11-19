# Phân tích thất bại của staged workflow

Sáu lượt development, không phải kết luận tổng quát về model.

## 12B: hành động thiếu quan sát và lặp lỗi edit

Cả ba lượt staged không có load_skill/run_skill_script. Do đã bỏ read_file và run_command trực tiếp, model không đọc source bằng interface mới mà thử edit. Packaging có 45 edit_file requests, 42 FileEditError; w3lib có 11 write_file requests đều thiếu filepath. Platformdirs có 7 edit failures rồi 40 write_file requests, patch source cuối không có thay đổi. Đây là lỗi tương tác tool và phục hồi, không phải bằng chứng riêng về năng lực lập trình.

## 31B: interface skill phức tạp và sửa quá hẹp

Packaging có 42 run_skill_script requests và 37 INVALID_ARGUMENTS, chủ yếu thiếu skill_name hoặc ghép field vào file_path. W3lib có 11 FileEditError và chỉ còn file tái hiện lỗi trong patch. Platformdirs tới được submitter, sửa source và pass 3 test tự viết, nhưng chấm độc lập vẫn 61 fail / 748 pass: patch chưa bao phủ đầy đủ hành vi cần kiểm chứng.

## Workflow của chúng ta cũng góp phần

12B mất tool đọc quen thuộc nhưng không chuyển sang skill. Interface yêu cầu skill_name + file_path + args lồng nhau làm tăng cơ hội gọi sai. Script hard-cap chặn inspection, nhưng không chặn lặp edit sai hoặc buộc editor kết thúc; 5/6 lượt không qua editor. Compiler pass và fixture tests chỉ chứng minh cơ chế, không chứng minh phù hợp với model thật.

## Chưa xác định nguyên nhân gốc ở weights hay parser

Trace lưu arguments đã qua parser. Chưa có phép đối chiếu raw model output với parser hoặc ablation riêng cho compaction/template. Do đó chưa quy lỗi cho quantization, tham số, training hoặc vLLM parser. Cần kiểm thử tool-call trên fixture có đáp án biết trước, tách khỏi bài sửa repo.

## Ưu tiên tiếp theo

Đo và đơn giản hóa giao diện tool trước khi thêm agent. Kiểm tra các ca read/edit/write có schema tối giản; xác nhận raw output và arguments parsed; chạy sửa file nhỏ có kiểm chứng. Sau khi model dùng tool ổn định mới thử lại workflow staged, với editor có cách đọc source đáng tin và cơ chế handoff có thể kiểm chứng. Chưa nên tăng budget hoặc fine-tune từ sáu lượt này.
