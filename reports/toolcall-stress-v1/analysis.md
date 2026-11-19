Kết quả: hoàn tất 24/24 capture, không thực thi tool.

| Nhánh | 12B đúng chính xác | 31B đúng chính xác |
|---|---:|---:|
| Direct, prompt ngắn | 3/4 | 4/4 |
| Direct, context dài | 3/4 | 4/4 |
| Skill, prompt ngắn | 3/4 | 3/4 |

Đây là số quan sát trong một lượt chạy, không phải ước lượng tỷ lệ thành công trên task thực tế. Skill có giao diện và bộ case khác; không gộp ba nhánh thành điểm chung.

12B: ở cả short_direct và long_direct, yêu cầu edit_exact_line nhưng raw output chọn read_file. API và parser replay giữ đúng lựa chọn đó. Đây là sai khác từ output được sinh so với yêu cầu, không phải parser biến edit thành read. Probe yêu cầu một call chính xác; trong workflow thực, đọc trước khi sửa có thể hợp lý, nên kết quả này chưa chứng minh model không biết edit.

Cả hai model: case skill/read_object phát đúng object với start:17,end:31 trong raw output, nhưng API trả start:"17",end:"31". Parser replay tái hiện đúng khác biệt này. Source vLLM parser/gemma4.py giữ bare scalar thành chuỗi; schema args là object mở, không khai báo kiểu cho start/end. Phân loại tự động parser_mismatch_suspected ở đây chỉ là khác biệt kiểu dữ liệu, không phải mất key hay JSON hỏng. Với CLI skill hiện tại, số chuyển thành chuỗi có thể vẫn tương đương khi thực thi; chưa chạy tool nên chưa đo ảnh hưởng thực tế. Các case list và object chỉ có path đều đúng.

Tất cả 24 engine replay khớp API. 22/24 native interpretation khớp API chính xác; hai khác biệt là ép kiểu nêu trên. Tám case dài có input8193 token, nằm trong8192±128; không có truncation. Chưa thấy context dài làm giảm kết quả của bộ bốn case này. Dữ liệu nền tổng hợp một message không thay thế lịch sử agent nhiều lượt.

Bước tiếp theo nên giữ riêng: (A) kiểm tra thực thi skill list/object để đo ảnh hưởng chuyển kiểu; (B) replay lịch sử thực của một task thất bại, rồi đổi duy nhất giao diện tool sang list phẳng. Không dùng kết quả probe một-call làm bằng chứng agent đã giải được repository task.

Ghi nhận vận hành: batch hoàn tất bằng service gemma-toolcall-stress-v1, tự dừng, không có trigger chạy lại định kỳ. Báo cáo cuối được dựng lại từ24 artifact. Import trùng tên module report khiến cập nhật bảng giữa batch dùng nhầm generator; đã sửa sau khi batch kết thúc. Frozen-inputs.json vẫn giữ hash source thực tế lúc chạy; thay đổi sau chạy chỉ sửa routing báo cáo và phần trình bày, không sửa capture hay classifier.
