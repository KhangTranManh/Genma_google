Hoàn tất hai trajectory, mỗi model3 generations (candidate đầu +2 lần sửa lại). Tổng6 captures,12 lần thực thi riêng raw/API và2 lần grade độc lập candidate API cuối. Service tự dừng. Kiểm tra hash trước khi dựng phân tích cuối: mọi source/input trong frozen-inputs.json giữ nguyên trong thời gian batch. Sau batch chỉ bổ sung hiển thị capture_label vào report, không sửa capture/execution.

| Model | Candidate đầu | Sửa lại lần1 | Sửa lại lần2 | Grader cuối |
|---|---|---|---|---|
|12B|Edit được, vẫn chậm|Chủ yếu thêm newline, vẫn chậm|Đổi quantifier, làm hỏng chức năng và vẫn chậm|Không đạt|
|31B|Edit được, vẫn chậm|Đổi regex, vẫn chậm|Output512 token bị cắt, không có call hợp lệ; giữ source trước|Không đạt|

Tất cả6 candidate đều không qua public diagnostic. Năm capture hoàn chỉnh có raw/API arguments khớp và old_string khớp source. Capture cuối31B bị truncation; raw_equals_api=null nghĩa là chưa so sánh được, không phải có bằng chứng parser làm sai. Không tự tăng budget hoặc cấp thêm lượt sau lỗi.

12B: candidate đầu chọn <base\s+[^>]*?href...; lần sửa lại đầu không đổi thuật toán, chủ yếu thêm newline cuối block. Lần sửa cuối chọn <base\s+[^>]+?href..., loại bỏ khả năng không có ký tự giữa whitespace và href, làm test chức năng thất bại và trả rỗng với URL bình thường. Grader cuối còn timeout ở30000.

31B: candidate đầu <base\s[^>]*?href..., sau feedback thêm dấu+ cho whitespace nhưng vẫn để [^>]*? quét qua các dấu<. Candidate cuối xuất nội dung bị cắt, không thành tool call; source giữ nguyên sau lần sửa đầu. Grader cuối qua67 test chức năng nhưng vẫn timeout ở30000.

Phản hồi công khai gồm tool response, đo6000 (3 mẫu, median≤0.2s, timeout2s) và test chức năng. Nó không tiết lộ cách sửa hay biểu thức đúng. Grader cuối2K/4K/8K/30K và các trường hợp URL không đưa vào prompt. Cả public diagnostic và grader độc lập đã preflight baseline fail/fixed pass. Candidate cuối được grade bất kể public pass/fail; kết quả grader cuối không cấp thêm lượt sửa.

Kết luận trong setup này: thêm phản hồi đúng/sai cùng số liệu runtime chưa đủ khiến hai model đổi sang cách sửa đạt yêu cầu.12B có biểu hiện thay đổi ít ý nghĩa rồi gây regression;31B thay đổi không xử lý căn nguyên và vướng output budget cuối. Đây là kết quả mô hình cùng harness/ngân sách: host vẫn cấp vị trí và block, fresh prompt dựng lại lịch sử, thinking off, output512. Không suy ra phản hồi vô ích nói chung hay model hoàn toàn không biết debug.

Giới hạn so sánh: chỉ một issue công khai đã quan sát; không có blind-retry control hoặc cùng ngân sách one-shot, nên không ước lượng tác động nhân quả của feedback. Feedback input chứa tool diff và test output tương đối dài; không tách được ảnh hưởng của cách trình bày. Bước tiếp nên tách hai yếu tố: (A) giữ feedback, tăng output budget512→1536 để kiểm tra truncation; (B) giữ budget, rút feedback thành command/exit/timing và yêu cầu chẩn đoán nguyên nhân trước edit. Không gộp hai thay đổi vào một nhánh. Chưa chạy hai nhánh này.
