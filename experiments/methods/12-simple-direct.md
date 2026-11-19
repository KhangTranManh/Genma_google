# Simple direct v1: kiểm tra lại từ giao diện tối giản

Mỗi model 12B/31B dùng một LlmAgent với sáu tool chính thức: run_command,
read_file, edit_file, write_file, get_status, submit_patch. Không skill, subagent,
script API lồng nhau, chặn đọc riêng hay host auto-submit.

## Hai tầng đo, không gộp điểm

1. **Bốn synthetic diagnostics:** 2 model × (sửa hàm increment sai; tạo module hello).
   Dùng compiler, ADK Runner và SwegemmaContext tools thật với model đang serve,
   không dùng model giả. Có public tests, 16 LLM calls / 24 tool calls / 240 giây.
   Chỉ pass khi model tự submit patch không rỗng, có ít nhất một tool response thành
   công cho từng tool yêu cầu và grader độc lập trong container sạch pass.
   Patch chạy lại public tests và các giá trị grader khác. Giới hạn này chỉ dành
   cho chẩn đoán API đơn giản, không so ngang với bài repo thật.
2. **12 real development trials:** 2 model × 3 issue đã xem × (simple/control).
   Dùng evaluator của ban tổ chức. Simple chỉ rút gọn system prompt; control là
   flat R1 cũ với cùng 6 tools. Cùng 48 calls / 96 tools / 15 phút / context16k.

Prompt mới nhấn mạnh đọc source trước sửa, old_string ngắn và chính xác,
filepath là trường riêng bắt buộc của write_file, không lặp nguyên thao tác lỗi,
không viết lại module từ trí nhớ; test và submit trực tiếp. Không ép model gọi
một lớp skill mới để đọc source.

## Điều kiện diễn giải

- Synthetic pass chỉ chứng minh model dùng được các tool cơ bản trên fixture,
  không chứng minh giải được issue thật hoặc vượt leaderboard 0.29.
- Nếu synthetic fail, xem tool response, arguments và độc lập grader; không quy
  ngay cho weights. ADK events hiện vẫn là dữ liệu sau parser, chưa có raw token
  ablation để kết luận lỗi parser.
- Đếm tool errors gồm cả lệnh test thất bại; cần phân loại trước khi kết luận lỗi
  gọi API. Không yêu cầu zero errors nếu model đã phục hồi và sửa đúng.
- Repo thật: explicit model submit + resolved=true là tiêu chí chính; patch fallback
  pass báo riêng. Giảm read/time nhưng không pass thì chưa coi là cải thiện.
- Tất cả task thật đã được xem trong development. Chưa phải holdout; chưa có
  khẳng định thống kê từ một lượt/cell. Không thay cấu hình giữa đợt.

## Chuẩn bị và lưu bằng chứng

Thử khởi động trước đóng băng: 12B edit_existing đã pass trong 12.585s nhưng fixture
ban đầu chưa ignore cache artifacts. Kết quả đó giữ riêng tại runs/simple-smoke/,
không tính vào bốn lượt chính thức. Fixture chính thức có .gitignore cho cache và
chỉ định lệnh test nhất quán. Cả bốn diagnostics sẽ chạy mới sau khi đóng băng.

Nguồn: experiments/prompts/simple_v1/system.md và submission_candidates/simple_v1/.
Kết quả: runs/simple-v1/, reports/simple-v1/comparison.html. Mỗi job lưu events/trace,
patch, summary; real jobs có submission snapshot và input hashes. Micro grader
không được gửi cho model và không chạy repository code trên host.

Trigger worker và observer độc lập dùng chung GPU lock với các đợt trước; tự dừng
ở complete/needs_review. Lỗi runtime/endpoint/context dừng để điều tra; không đổi
model hoặc tăng budget âm thầm. Các kết quả cũ được giữ nguyên.
