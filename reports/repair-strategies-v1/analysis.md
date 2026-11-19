Đã hoàn tất tuần tự A→B→C cho12B và31B:17 edit generations +4 decision calls =21 model calls,34 raw/API candidate executions và6 final independent grades. Các arm dừng sớm đúng luật khi public check pass. Service đã dừng; kết quả cũ không ghi đè.

| Nhánh |12B|31B|
|---|---|---|
|A: ceiling1536, feedback cũ|Qua grader đóng băng nhưng hỏng tag có attribute dài|Không còn truncation; vẫn trượt performance|
|B: chẩn đoán riêng rồi edit|Sửa sai, trượt chức năng và performance|Một edit bị cắt; patch cuối vẫn chậm|
|C:3 candidates độc lập|Cả3 vẫn chậm; candidate chọn không đạt|Cả3 vẫn chậm; candidate chọn không đạt|

Không có final candidate nào đạt cả grader gốc và audit bổ sung. Kết quả này chỉ trên một issue công khai đã quan sát, với host cấp sẵn block và native API; không phải solve rate hay điểm Kaggle.

A12B là phát hiện quan trọng về grader: model chặn tìm kiếm bằng [^>]{0,100}?; qua67 test và kiểm tra hiệu năng nhưng bỏ sót tag hợp lệ có thêm attribute dài200/1000. Audit được bổ sung SAU khi quan sát patch, ghi riêng posthoc-semantic-audit.json, không đổi grader đóng băng, không đưa feedback cho model và không dùng để chọn candidate. Baseline qua các case audit. verified_local_fix=True trong bảng là pass của grader gốc; accepted_after_audit mới kết hợp với audit bổ sung, cả6 candidate cuối đềuFalse. Audit cũng chưa bảo đảm đúng mọi input.

A ceiling lớn chỉ giải quyết triệu chứng truncation đã thấy ở31B baseline512; lần này31B sinh146/149/148 tokens, không dùng đến trần1536 nhưng vẫn sửa sai.12B dùng141+149 tokens và dừng sớm theo public check. Khác biệt patch so baseline lịch sử không thể quy hết cho ceiling: runtime feedback thay đổi và inference không bảo đảm tái lập bit-for-bit.

B31B có decision summary nhắc tránh vượt tag boundary, nhưng edit không hiện thực hóa: một lần bị cắt1152 token, lần cuối lặp cấu trúc cũ. B12B nêu backtracking nhưng đề xuất quantifier vẫn sai, thậm chí tự thêm patch vào summary dù yêu cầu chỉ ba trường. Vì vậy summary có thuật ngữ đúng không chứng minh có phương án đúng. Tất cả4 decision responses finish_reason=stop; không có diagnosis truncation, khác với edit truncation. B12B qua posthoc tag-extra nhưng vẫn trượt các URL/test chức năng gốc; các lớp đánh giá đo riêng, không thay thế nhau.

C dùngsampling0.6/seeds17/29/43 nhưng phần lớn patch chỉ khác whitespace/lazy quantifier hoặcDOTALL. Ba samples không tạo đa dạng thuật toán đáng kể; xếp hạng public runtime không cứu được nhóm candidate đều sai. Không dùng final independent outcome để chọn lại.

Ngân sách: cùng trần4608 generated tokens/model choA/B/C, nhưng actual không bằng nhau. Tổng thực dùng4300 output tokens trên6 model-arm pairs (đã gồm decision summaries). B tốn input/calls và overhead hơn A/C; equal maximum tokens không phải equal compute. B chia1536 thành384 summary+1152 edit trong mỗi retry; C thaytemperature, nên không phải so sánh chỉ một yếu tố prompt giữa cả ba. Không có nhiều seed trajectories choA/B hoặc tập issue độc lập; không đưa kết luận thống kê.

Source/input hashes của cả ba arm đã được đối chiếu và không đổi sau khi inference hoàn tất, trước các sửa trình bày báo cáo. Sau run chỉ bổ sung hiển thị decision artifacts vào report B và audit columns ở bảng tổng; không sửa classifier, generation, edit, grader hoặc selection. Hash gốc vẫn giữ trong từng runs/*/frozen-inputs.json.

Hướng tiếp nên tách rõ hai giả thuyết: một nhánh buộc nêu bằng chứng có thể kiểm tra cho phương án mới trước khi edit; một nhánh thử reasoning/thinking hoặc model settings khác, giữ nhiệm vụ và grader. Trước khi chạy, bổ sung các case chức năng còn thiếu vào grader mới có version riêng, kiểm tra lại baseline/fixed, rồi đánh giá thêm issue mới. Không tiếp tục tối ưu riêng issue này rồi coi là năng lực tổng quát. Chưa chạy các nhánh tiếp theo này.
