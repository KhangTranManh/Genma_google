Audit đã hoàn tất9/9 hồ sơ, gồm8 old-skipped và1 old-allowed control. Mọi hồ sơ được gọi Patch mới từ code gốc; không deduplicate trước audit.9 generation captures hoàn chỉnh, API/raw khớp9/9, edit hợp lệ9/9; không truncation, không infrastructure missing. Tổng1316 output tokens. Public và independent tests chấm từng candidate, không dùng để cấp retry hoặc sửa candidate. Source/input hashes giữ nguyên trong inference/grading, xác nhận runs/gate-audit-v1/hash-audit.json.

| Nhóm | Được audit | Patch verified pass |
|---|---:|---:|
|12B, bị skip|3|0|
|31B, bị skip|5|0|
|31B, old-allowed control|1|0|

Tất cả9 candidate qua67 test chức năng và semantic check thuộc tính dài, nhưng không đạt reproducer/public performance và independent performance regression. Đây là failure về hành vi hiệu năng của patch, không phải do tool không sửa được file. Một generation/hypothesis, cùng issue đã quan sát nhiều lần, hypotheses cùng trajectory phụ thuộc nhau.

Kết luận đúng: audit này chưa quan sát gate loại mất một patch pass. missed_success_yield trong8 skipped scorable attempts là0/8 ở mẫu này. False-negative rate among successful patches KHÔNG XÁC ĐỊNH vì0 successes cả skipped và allowed (0/0). Không được ghi gate FNR0%, accuracy100%, hoặc gate đã được chứng minh tốt. Tất cả candidates fail thì không thể kiểm tra quan hệ giữa prediction accuracy và patch correctness. Muốn ước lượng quan hệ cần nhiều issue/trajectory có cả positive patch outcomes, không tăng mẫu bằng cách coi nhiều hypotheses trên cùng issue là task độc lập.

Prompt audit được tái tạo từ template của source branch và hypothesis đã commit; old-allowed prompt so sánh khớp chính xác archived request. Control được sinh lại trong cùng audit; old historical result không thay thế control mới. Capture/API/native cùng generation, grader preflight fresh xác nhận base fail và diagnostic fixed pass cả public/independent/semantic. Không đưa fixed expression hay audit outcomes cho model.

Replay evaluator trên fixed pool:3 trajectories×3 policies(original order/old gate/rank-only)×3 patch budgets1/2/3=27 conditions. Không condition nào tìm được verified pass vì pool không có patch pass. Rank-only thử được các candidates mà old gate bỏ qua, nhưng đây là thay đổi coverage/cost, chưa phải improvement về solve rate. Không coi replay này là online run hay adaptive-agent result. Không dùng independent outcome để sắp thứ tự; evaluator chỉ dùng label để tính metric sau khi thứ tự đã xác định.

Grouping theo vector chính xác: role-probes12B có3 IDs nhưng1 vector; role-probes31B3 IDs/2 vectors; revise-hyp31B3 IDs/1 vector. Không group xuyên catalog/phase. Đây là duplicate_on_catalog, chưa phải cùng mechanism hay cùng patch khả thi. Audit vẫn chạy tất cả9 member để tránh che khuất gate/grouping loại nhầm. Chưa chạy NEW_HYPOTHESIS khi unique-vector-count1; đó là nhánh riêng đã định nghĩa.

Policy mới được định nghĩa là rank-only, không bật hard pruning. Severe-contradiction3/4 chỉ là flag không thay eligibility cho tới khi có bằng chứng audit tốt hơn; miss1/6 không tự loại. Các phần group/diversity, proposed probe DSL và optional revision có spec/config/helper/schema nhưng chưa có model experiment mới. Proposed-probe sandbox adapter chưa triển khai. Review chưa thử model-proposed discrimination hoặc chứng minh các phần2–5 giúp viết patch đúng.

Điều chỉnh kết luận trước: việc Python chặn edit chỉ chứng minh rule được thực thi. Trước audit, khả năng Patch của8 hồ sơ bị skip là unknown. Sau audit một lượt, chúng fail trong cấu hình này nhưng chưa đủ đánh giá gate tổng quát. Giữ reports cũ như lịch sử; báo cáo này bổ sung counterfactual evidence và giới hạn suy luận.
