Hoàn tất12/12 điều kiện và24 lần thực thi riêng (raw/API). Service tự dừng. Source/input hash frozen đều giữ nguyên trong suốt lượt chạy.

| Model | Có chỉ dẫn sửa: đạt local grader | Tự suy ra: đạt local grader |
|---|---:|---:|
|12B|3/3|0/3|
|31B|3/3|0/3|

Mỗi bộ3 gồm context ngắn,4K,12K; chỉ một generation/điều kiện, một issue đã quan sát trước. Không phải tỷ lệ thành công trên benchmark.

Tất cả12 call hợp lệ, old_string khớp nguyên văn source, edit thật thành công. Raw/API khớp12/12; installed parser replay khớp API12/12. Raw/API execution cho cùng phân loại12/12. Tất cả qua67 test chức năng. Không thấy lỗi chép chuỗi hoặc parser trong lượt này.

Nhánh có chỉ dẫn: cả hai model tạo được thay đổi xử lý lỗi; input30000 chạy khoảng0.0014 giây trong phép đo local. Nhánh tự suy ra:12B chọn đổi thành <base\s+[^>]*?href...,31B chọn <base\s[^>]*?href...; cả hai dùng quantifier lazy nhưng vẫn timeout3 giây ở input30000. Tỷ số thời gian8K/2K khoảng15.9–19.1 lần, phù hợp với việc chưa loại bỏ tăng trưởng gần bậc hai ở các kích thước đã đo. Đây là suy luận từ patch và phép đo, không phải chứng minh độ phức tạp cho mọi input.

Grader preflight: baseline qua67 test nhưng timing2K≈0.0773s,4K≈0.3094s,8K≈1.2539s,30K timeout3s. Host diagnostic fixed qua chức năng và30K≈0.001385s. Có ba mẫu/kích thước, ngoại trừ điểm timeout thì dừng sớm; ngưỡng đã định trước, không chỉnh theo output model. Raw/API được grade độc lập trong container sạch. Không yêu cầu patch giống reference và không đọc reference patch.

Kết luận trong phạm vi thí nghiệm: nút thắt không chỉ là đọc/loay hoay. Khi đã cung cấp chính xác vị trí và đoạn code, cả hai thao tác edit tốt nhưng vẫn chọn cách sửa không giải quyết lỗi khi bỏ hướng dẫn thuật toán. Thêm code tham khảo lên12K không đổi kết quả ở issue này. Prompt làm kỹ hiện tại chưa đủ giúp suy ra phương án hiệu năng đúng. Chưa loại trừ ảnh hưởng của thinking off, output512, one-shot và không có phản hồi chạy test; không kết luận năng lực tổng quát của hai model.

Bước tiếp nên là một nhánh có phản hồi, giữ tách khỏi one-shot này: model tạo candidate đầu, nhận kết quả kiểm tra tái hiện công khai có giới hạn, được sửa lại tối đa2 lần; vẫn giữ một bộ kiểm tra độc lập không tiết lộ. So sánh với one-shot cùng issue và ngân sách tổng đã công bố. Nhánh ADK với input giống hệt vẫn là kiểm tra adapter riêng, chưa được chạy ở đây.
