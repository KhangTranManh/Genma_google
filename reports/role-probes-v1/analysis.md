Đã triển khai và chạy role-probes-v1. Objective pipeline hoàn tất cho cả12B/31B; status complete_with_unavailable_feedback vì một advisory review của31B bị truncation. Không gọi lại model, không suy diễn partial JSON. Source/input hash không đổi trong inference; hash-audit-before-postrun-fix.json ghi xác nhận. Sau inference sửa lỗi điều phối để RuntimeError/ValueError của optional reviewer được lưu unavailable và không chặn quyết định Python; snapshot worker-at-inference.py giữ source thực dùng. Việc chốt bookkeeping không được tính là thêm model call hay một review thành công.

| Model | Giả thuyết | Mâu thuẫn probe | Chưa phân biệt được | Patch chạy | Patch giữ/chọn |
|---|---:|---:|---:|---:|---:|
|12B|3|3|0|0|0|
|31B|3|1|1|1|0|

Cả hai model không có patch được chọn. Không chạy independent final grader vì không có retained candidate; null không đồng nghĩa hidden test đã chạy và fail. Một patch31B thực thi raw/API riêng trên code gốc, tool ok, raw/API khớp; vẫn trượt hiệu năng public6000 nên bị loại. Không có lỗi parser quan sát ở patch này.

Probe gốc: repeated_open≈0.705s (slow); single_open≈0.000059s, closed_tags≈0.000284s, plain_text≈0.000022s (fast). Ba lần đo mỗi case, function time loại startup; fast≤0.05s,slow≥0.2s, grayzone uncertain. Diagnostic fixed pass toàn bộ probe/public checks nhưng implementation và kết quả fixed không đưa cho model. Các phép đo được cache trong preflight trước Localize, chỉ reveal sau khi đã lưu predictions; không nói rằng đã đo mới sau prediction.

12B: cả3 giả thuyết dự đoán repeated_open/single_open/closed_tags đều slow, plain_text fast. Hai dự đoán control bị phép đo bác bỏ trong cả3. Python không cấp edit budget. Đây là refutation của predicted outcomes cụ thể, không phải chứng minh mọi biến thể của nguyên nhân backtracking sai. Ba hypothesis còn dùng từ .* khi source thực là [^>]*; cách diễn đạt thiếu chính xác cần được đối chiếu source. Không tự tạo giả thuyết mới thay model và không chạy lại cho đến khi đoán đúng.

31B: hai hypothesis có cùng dự đoán slow/fast/fast/fast và khớp4/4 probe; catalog chưa phân biệt được chúng nên Python chỉ thử một đại diện. Một hypothesis khác dự đoán cả plain_text slow nên không eligible. Patch đại diện vẫn chọn lazy quantifier và whitespace+, không loại bỏ lỗi hiệu năng. Như vậy dự đoán đúng một tập probe chưa bảo đảm chọn cách sửa đúng; nó cũng chưa chứng minh cơ chế causal duy nhất.

Vai review31B xuất hai trường đầu rồi lặp whitespace đến512 tokens; finish_reason=length, thiếu JSON hoàn chỉnh. Không nhận hypothesis_status/patch_status từ partial output. Candidate decision đã được Python tính xong nên chốt không chọn patch không phụ thuộc reviewer. Đây cũng là giới hạn của structured-output generation trong lượt này; không đủ bằng chứng quy về weights hay vLLM constrained decoder. Không chữa bằng tăng budget ngầm. Cải tiến điều phối sau run chưa được thử lại bằng một model run mới.

So với role-split-v1: trước đó6 patch calls/2models,14 calls tổng; lượt này2 Localize+1 Patch+1 review=4 calls tổng, chỉ1 patch. Gate giảm calls và ngăn nhánh với dự đoán sai đi tiếp, nhưng không nâng solve result (vẫn0 selected). Khác budget, thêm probe information và thay review schema cùng lúc; không phải causal ablation của một yếu tố và không đo năng lực trên tập task mới.

Hạn chế gate: fixed catalog chỉ quan sát timing classes trên4 input patterns, không bao phủ mọi cơ chế; gom các dự đoán chưa phân biệt có thể bỏ qua một cách sửa tốt. Có thể chặn nguyên nhân nhìn chung đúng chỉ vì model dự đoán một control sai. Đây là policy tìm kiếm bảo thủ, không phải định lý bác bỏ giả thuyết. SBFL vẫn chỉ là weak tie-breaker và không có exception stack trace. Source location/đoạn code vẫn được host chỉ sẵn.

Bước tiếp nên tách riêng: cho một lần REVISE_HYPOTHESIS sau khi nhận probe contradictions, tuyệt đối chưa edit; vẫn yêu cầu dự đoán cho một probe mới chưa reveal để tránh chỉ chép lại đáp án đo. Giữ kiểm tra patch khách quan và reviewer optional. Mở rộng sang issue mới trước khi kết luận tổng quát. Chưa chạy bước tiếp này.
