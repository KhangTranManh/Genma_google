# Bước 1: định nghĩa phép kiểm tra tool-call và parser

Trạng thái: chỉ định nghĩa, xuất schema và kiểm tra dữ liệu; chưa gửi inference,
chưa thực thi tool, chưa khởi động trigger hoặc chuyển model/GPU.

## Câu hỏi duy nhất

Arguments sai đã có trong token model sinh ra, hay bị biến đổi trong bước parse/
chuyển schema? Không thêm agent, skill, sửa prompt sửa-repo, tăng budget hoặc train
model trong cùng phép thử. Đây là chẩn đoán giao diện, không chấm năng lực sửa code.

## Bốn case đầu, cho cả 12B và 31B

| Case | Cần giữ chính xác |
|---|---|
| read_range | filepath và start_line/end_line dạng số nguyên |
| write_quotes_newlines | filepath riêng; nội dung có dấu nháy và newline |
| edit_exact_line | filepath, old_string/new_string có bốn dấu cách đầu dòng |
| run_test_command | một command string không bị tách/ghép field |

Dùng cùng bốn tool schemas cho mọi case, không chỉ hiện tool đích. Schema lấy từ
SwegemmaContext và đúng bộ chuyển FunctionTool → LiteLLM của ADK đang cài; không
viết schema tối giản khác rồi coi là phép thử harness hiện tại. Lưu byte/hash và
versions khi xuất. Tám requests ban đầu (4 × 2 model), một mẫu/case chỉ dùng để
kiểm tra quy trình capture. Chưa kết luận tỷ lệ lỗi hoặc khác biệt model.

## Thu raw và parsed từ CÙNG một lần sinh

1. Gửi request chat-completions native tool_choice=auto, stream=false,
   return_token_ids=true, skip_special_tokens=false, temperature=0,
   max_tokens=512, thinking=false. Lưu request đầy đủ.
2. Lưu nguyên response: content/reasoning, tool_calls, finish_reason, stop_reason,
   usage và choice.token_ids. Không sửa arguments hay tự thêm field thiếu.
3. Decode output token IDs bằng tokenizer đúng checkpoint/revision, giữ special
   tokens. Lưu IDs và raw-decoded riêng, cùng hash tokenizer/config/runtime.
4. Đối chiếu native Gemma tool-call format với tên tool và arguments API trả về.
   Raw native format không phải JSON; không dùng json.loads(raw) để kết luận model
   sai. So tên, key, kiểu số, string, whitespace, newline và escaping theo ngữ nghĩa.
5. Nếu cần replay, dùng parser engine đang cài đúng phiên bản/config trên cùng raw
   output. Utility/fallback parser là kiểm tra phụ, không mặc định tương đương API.

Đã kiểm tra source vLLM 0.33.0 cục bộ: non-streaming response có thể trả
choice.token_ids khi return_token_ids được bật và metadata không bị suppress.
Đó mới là kiểm tra khả năng từ source, CHƯA xác nhận server trả dữ liệu thực tế.
Nếu IDs vắng hoặc output bị cắt, ghi missing_raw_capture/truncated; không đoán.
Không gọi hai lần riêng rồi coi chênh lệch là lỗi parser, dù seed/temperature giống.

## Nhãn kết quả và điều kiện kết luận

- correct: raw và parsed khớp tool/args mong đợi về kiểu và nội dung.
- raw_output_defect: có đủ raw, nó đã thiếu/sai thông tin hoặc sai native syntax.
  Đây là lỗi đầu ra trong cấu hình này; chưa chứng minh lỗi weights cố hữu.
- parser_mismatch_suspected: raw hợp lệ có thông tin đúng nhưng parsed đổi/mất;
  cần replay đúng engine trước khi gán nguyên nhân cho parser.
- schema_or_adapter_issue_suspected: dữ liệu đúng tại API nhưng sai sau adapter,
  hoặc schema quảng bá sai contract; phải thu được dữ liệu ở cả hai điểm trước
  khi xác nhận. Bước đầu direct-API chưa đủ để tự xác nhận lỗi adapter.
- truncated / missing_raw_capture / ambiguous: thiếu điều kiện để phân loại.

Không hard-code nhận dạng một mẫu string lỗi rồi tự đoán field hoặc unescape.
Không chạy tool trả về: mọi filepath/command chỉ là dữ liệu synthetic, không đọc
repo, không gửi gold patch/test và không làm bẩn workspace.

## Phần triển khai sau, theo từng bước

Bước này chỉ có plan, cases và schemas. Bước sau: 1 request kiểm chứng capture trên
model đang serve → kiểm IDs/decoder → mới mở 8 cases → nếu có lỗi mới replay parser
và đối chiếu adapter. Streaming, long-context, lỗi phục hồi và huấn luyện để riêng.
Không suy kết luận parser từ log cũ vốn chỉ chứa arguments đã parse.

Artifacts tương lai: runs/toolcall-probe-v1/{model}/{case}/, gồm request/response,
output-token-ids/raw-decoded/parsed-calls, classification và runtime metadata.
Definition hiện có ở reports/toolcall-probe-v1/definition.json. Không có job chạy.

## Kết quả thực thi bước 1

Đã chạy đủ 8 requests, không thực thi tool. 31B chạy trước để tái sử dụng server,
sau đó 12B; một mẫu mỗi case/model. Cả tám có token IDs cùng-generation, decode
giữ special tokens, independent flat decoder và Gemma4Parser engine replay khớp
arguments API. Tokenizer cleanup không được bật (default false trong bản đang cài).

31B đúng 4/4 yêu cầu. 12B đúng 3/4; case edit_exact_line sinh read_file ngay ở raw
output. Nhãn raw_output_defect ở đây chỉ nghĩa lệch yêu cầu chọn tool, không phải
format native sai. Chưa tái hiện parser làm hỏng arguments trong tám ca nhỏ.

Không suy kết luận trên streaming, context dài, nested skill args hoặc ADK adapter.
Xem reports/toolcall-probe-v1/comparison.html và raw/response/replay từng case.
