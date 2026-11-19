B hoàn tất6 edit generations +4 decision calls; cả hai model không đạt grader cuối.12B trượt chức năng và performance;31B qua chức năng nhưng trượt performance. Đây là một issue được cung cấp exact block, không phải benchmark năng lực chung.

12B: bản chẩn đoán nhắc tới backtracking nhưng đề xuất [^>]+? rồi [^>]+, không loại bỏ quét qua các dấu<. Lần sửa cuối làm hỏng URL bình thường. Một số decision summaries còn tự sinh đoạn patch dù được yêu cầu chỉ ba trường ngắn; cần kiểm tra response finish_reason trước khi gọi nó là chẩn đoán hoàn chỉnh.

31B: summary đã nhắc không vượt qua tag boundaries, nhưng edit lần1 bị cắt1152 token và edit lần2 giữ nguyên cấu trúc regex chậm. Có khoảng cách giữa mô tả nguyên nhân và hành động thực tế. Không thể kết luận thêm bước nói nguyên nhân sẽ tự động cải thiện patch.

Budget tối đa4608/model như A nhưng B chia thành các decision calls384 và edit1152 ở mỗi retry; số calls/input và phân bổ token khác A. Chỉ một trajectory/model, không phải phép chứng minh nhân quả hay kết luận reflection vô ích. Grader và feedback giữ nguyên; source hash kiểm tra riêng sau batch.
