# Staged workflow v1 — thử quy tắc thực thi trong YAML và skill

Đây là candidate dùng compiler/runtime chính thức, không phải thay vòng lặp host.
Các model/agent con trong mỗi gói đều dùng cùng Gemma variant. Không custom host
callback và không sửa source của đợt reading-v2 đang chạy.

## Candidate và đối chứng

- Flat: bản R1 focused-reading prompt, 6 tools như cũ; chạy lại trong đợt mới.
- Staged: SequentialAgent gồm planner → LoopAgent(editor/verifier, 2 vòng) → submitter.
- Cả hai model 31B và 12B; cùng ba issue development đã xem, tổng 12 lượt mới.
- 48 LLM calls / 96 tool calls / 15 phút, context16k, cùng compaction và Docker image.

Đây là bundle workflow + tool restriction + script budget. Không quy gain riêng
cho chỉ một thành phần. Không so độc lập model qua prompt khác nhau; mỗi model
có flat reference tương ứng. Một mẫu mỗi cell chưa chứng minh độ ổn định.

## Phần thực sự được cưỡng chế

| Stage/interface | Quy tắc thực thi |
|---|---|
| Planner | Không có tool; một phản hồi lập kế hoạch rồi SequentialAgent chuyển bước |
| Editor | edit_file/write_file/get_status và skill; không có generic run_command/read_file/submit_patch |
| Verifier | get_status và skill; không edit_file/write_file/submit_patch |
| Repair loop | Tối đa 2 vòng editor → verifier mỗi root invocation; tổng phiên vẫn bị giới hạn |
| Submitter | Chỉ get_status và submit_patch; không đọc/sửa/test bằng tool khác |
| Skill inspection | 8 successful search/read calls, tối đa 2 lần cùng request/read content; trả tối đa 80 dòng / 2400 ký tự |
| Skill test | Fixed pytest command, tối đa 4 lần, 45 giây/lần; không nhận arbitrary shell |
| Skill review | Tối đa 2 git diff --stat, không nhận shell input |

Skill state ở /tmp trong sandbox riêng mỗi issue; không ghi note vào patch. Search
literal và read chặn path traversal/symlink ngoài workspace/.git. Không nạp gold
patch hoặc test_patch cho agent. Các script chỉ chạy trong Docker qua executor ADK.

## Giới hạn cần nói rõ

- Compiler chưa có per-LlmAgent call quota được cấu hình trong YAML này. Agent con
  vẫn có thể gọi tool bị từ chối cho tới hết 48 calls; giới hạn script KHÔNG ép
  chuyển stage sau N LLM calls. Phải đo điều này trong trace, không tuyên bố đã fix.
- LoopAgent max_iterations=2 chỉ giới hạn số vòng các stage đã kết thúc, không
  giới hạn vòng tool nội bộ của một LlmAgent.
- Planner không có bằng chứng đọc thực tế; paths của nó là giả thuyết từ issue/tree.
- Skill không phải ranh giới an ninh chống model đối kháng: test/source do agent sửa
  vẫn là code thực thi trong sandbox. Không claim ngăn mọi cách đọc gián tiếp qua test.
- Kiểm tra pass vẫn do model diễn giải để quyết định submit; không có host auto-submit
  hoặc ép chấp nhận patch sai. Verifier fail thì có thể không nộp dù còn patch thu hồi.
- Stage prompts, API tools và skill script là package được hỗ trợ; tính cạnh tranh
  trên Kaggle chưa được chứng minh bằng compile hay fixture tests.

## Thực thi, bằng chứng, giữ nguyên thí nghiệm cũ

Queue chờ runs/reading-v2/state.json thành complete và dùng chung GPU-worker lock.
Không ngắt hoặc đổi model giữa job R0/R1/R2. Nếu reading-v2 needs_review, queue mới
vẫn chờ và hiển thị lý do, không giả vờ đang chạy model.

Đợt mới dùng runs/staged-v1/ và reports/staged-v1/comparison.html. Candidate và flat
reference có snapshot riêng; file/config/image hashes đóng băng trước job đầu.
Traces phân tích author để biết đã tới stage nào, script inspections/denials, native
reads, explicit submit và test pass. Đếm native read_file=0 trong staged không có
nghĩa không đọc file: phải xem cả run_skill_script read/search.

Tiêu chí chính: explicit model submit với patch không rỗng và resolved=true.
Giảm số read mà chất lượng giảm không được coi là cải thiện. Fallback patch pass,
không submit, budget exhaustion, context error và skill denial báo riêng.

## Artifacts

- configs/staged-study.toml
- submission_candidates/staged_v1/{flat,staged}/{12b,31b}/
- experiments/prompts/staged_v1/{planner,editor,verifier,submitter}.md
- experiments/skills/bounded-workspace/
- scripts/workflow/{build_staged,validate_staged,run_staged_task,staged_worker,staged_report}.py
- reports/staged-v1/{flat,staged}/*-validation.json and comparison.{html,md,json}

Harness có thể gọi lại root workflow khi agent chưa submit; do đó max_iterations=2 không có nghĩa chỉ hai vòng trong cả session. Skill budget vẫn giữ nguyên trong /tmp xuyên các invocation của cùng sandbox.
