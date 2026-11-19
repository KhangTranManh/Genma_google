Hoàn tất12/12 điều kiện. Cả hai model: control3/3, careful3/3; mỗi prompt gồm short,4K,12K. Raw/API arguments khớp12/12, installed parser replay khớp API12/12. Thực thi raw và API riêng trong repo sạch:24/24 lần đều tạo chính xác file mục tiêu. Tất cả8 điều kiện dài đạt độ dài trong khoảng mục tiêu±128;4K thực tế4095–4096,12K12288. Short control398 token, careful499 token. Không có lượt bị cắt do output length.

Không thấy lợi ích của prompt careful hoặc tác động giảm độ đúng do context trong bài này. Không thể suy ra prompt không hữu ích nói chung: bài đã được host chỉ rõ block và phép sửa, kết quả chạm trần. Chỉ một lần sinh mỗi cell, không đo xác suất thành công qua nhiều seed hay task.

Ý nghĩa với vòng lặp trước: model có thể giữ đúng escape/ký tự khi block liên quan nằm cuối context dài và thao tác được chỉ rõ. Lượt này không yêu cầu tự tìm vị trí, tự kết luận cách sửa, xử lý lỗi hay giữ trạng thái nhiều lượt; chưa đánh giá khả năng tự hoàn thành issue. Vì vậy tăng lượng input không tự giải quyết vòng lặp workflow; điểm cần kiểm tra tiếp là chuyển từ bằng chứng đọc sang edit và phần adapter ADK, với cùng input.

Giữ nguyên max_model_len16384; đây là tăng input chứ không phải thử server32K/64K. Context dài là code bổ sung từ repo, không phải lịch sử agent và không có needle ở giữa input.

Báo cáo cuối đã dựng lại trực tiếp từ12 execution artifact. Import report trùng tên khiến cập nhật giữa batch gọi nhầm generator; routing đã sửa sau batch. Frozen-inputs.json giữ nguyên source thực tế lúc chạy; thay đổi sau chạy chỉ ảnh hưởng routing báo cáo. Không sửa capture, arguments hoặc kết quả execution.
