Nhánh riêng: host cung cấp chính xác block3 dòng và yêu cầu đổi [^>]* thành [^<>]*. Mỗi model chỉ sinh một lần, chỉ được gọi edit_file. Raw call và API call được thực thi riêng bằng tool chính thức trong hai container sạch. Thành công ở đây là full file sau edit khớp chính xác thay đổi đã yêu cầu; chưa phải kiểm chứng giải issue hay benchmark hiệu năng.

Nhãn strict_arguments_label chỉ so khớp toàn bộ arguments với block kỳ vọng có newline cuối. Một replacement hợp lệ có thể không bao gồm newline đó: nếu exact_requested_result=True thì đó là edit thành công dù nhãn strict là raw_output_defect. Không dùng nhãn này để kết luận model edit sai.

So với stepwise-v1: trước đó cả hai thất bại khi old_string không khớp. Thí nghiệm này đồng thời rút ngắn context, cung cấp block chính xác, chỉ định rõ thay đổi, giới hạn còn một tool và chuyển adapter từ ADK sang native API. Vì nhiều yếu tố cùng đổi, kết quả chỉ cho thấy khả năng edit dưới điều kiện hướng dẫn cụ thể; chưa cô lập được một nguyên nhân duy nhất. Raw/API khớp trong lượt này không loại trừ parser lỗi ở lượt ADK trước.

Bước tách tiếp nên thay đổi từng yếu tố: giữ nguyên đoạn code và yêu cầu, so native API với ADK; sau đó giữ adapter và tăng context. Không gộp với điểm autonomous trước.

[
  {
    "model": "12b",
    "raw_equals_api": true,
    "engine_matches_api": true,
    "raw_execution_correct": true,
    "api_execution_correct": true,
    "strict_arguments_label": "raw_output_defect",
    "prompt_tokens": 398
  },
  {
    "model": "31b",
    "raw_equals_api": true,
    "engine_matches_api": true,
    "raw_execution_correct": true,
    "api_execution_correct": true,
    "strict_arguments_label": "raw_output_defect",
    "prompt_tokens": 398
  }
]
