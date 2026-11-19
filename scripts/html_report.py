"""Standalone, escaped HTML report built from saved experiment evidence."""
from html import escape
import json
from pathlib import Path


def e(value):
    return escape('—' if value is None else str(value), quote=True)


def score(value):
    if not value:
        return 'Chưa chấm'
    total = value.get('total', value.get('tests'))
    return f"{value.get('passed', 0)}/{total}" if total is not None else f"exit={value.get('exit_code')}"


def generate(root, report, comparison):
    comparison = comparison or {'rows': [], 'warnings': []}
    rows = comparison['rows']
    labels = {'progress_baseline_v1': 'A · Đối chứng', 'progress_guard_v1': 'B · Chống loop',
              'progress_finish_v1': 'C · Chốt có xác minh'}
    models = ['e4b', '12b', '31b']
    def table(headers, records):
        return '<div class="scroll"><table><thead><tr>' + ''.join('<th>' + e(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + e(x) + '</td>' for x in record) + '</tr>' for record in records) + '</tbody></table></div>'
    def link(path, label):
        return '<a href="../' + e(path) + '">' + e(label) + '</a>'
    expected = 9
    ended = [r for r in rows if r.get('status') not in ('running', 'prepared', None)]
    parts = ['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Báo cáo Gemma · So sánh ba model</title><style>',
        'body{font:16px/1.6 system-ui,sans-serif;background:#f3f6fa;color:#17263b;margin:0}main{max-width:1250px;margin:auto;padding:32px 20px}h1{line-height:1.2}h2{margin-top:36px}section,.notice{background:white;border:1px solid #dce3ed;border-radius:12px;padding:20px;margin:16px 0}.notice{border-left:5px solid #3264b0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e2e8f0;vertical-align:top}th{background:#edf3fb;white-space:nowrap}a{color:#2258a0}summary{cursor:pointer;font-weight:650}details{margin:12px 0;padding:12px;background:#f7f9fc;border-radius:8px}.muted{color:#57677c}nav a{margin-right:18px}code{overflow-wrap:anywhere} @media print{body{background:white}details{break-inside:avoid}main{padding:0}}',
        '</style><main><h1>Gemma local · Báo cáo so sánh ba model</h1>',
        '<p class="muted">Cập nhật UTC: ' + e(report['generated_at']) + ' · Điều phối: ' + e(report['controller'].get('status')) + '</p>',
        '<nav><a href="#compare">So sánh A/B/C</a><a href="#details">Từng lượt chạy</a><a href="#history">Các thí nghiệm trước</a></nav>',
        f'<div class="notice"><strong>Tiến độ A/B/C: {len(ended)}/{expected} lượt đã dừng.</strong> Bản này tự cập nhật theo trigger và được tổng kết khi lịch chạy kết thúc. Lượt bị lỗi hoặc chưa hoàn tất vẫn hiển thị đúng trạng thái.</div>',
        '<p>Cùng một issue URLKit, system prompt, vLLM và giới hạn 900 giây / 48 lượt / 96 thao tác. Đây là thử nghiệm local trên một issue, chưa phải điểm cuộc thi. Mỗi cấu hình chỉ chạy một lần/model; chưa đủ để kết luận model tốt nhất nói chung.</p>',
        '<section><h2>Các trường hợp chạy</h2><p><b>A — Đối chứng:</b> workflow cũ. <b>B — Chống loop:</b> theo dõi trạng thái, chặn thao tác lặp và chờ model tự submit. <b>C — Chốt có xác minh:</b> như B, thêm bước harness kiểm tra và chốt patch.</p><p><b>Nguồn nộp model</b> là model gọi submit; <b>harness</b> là bộ điều phối chốt. Patch thu hồi sau khi dừng chỉ dùng chẩn đoán, không tính thành công. Test độc lập chỉ chạy sau khi agent kết thúc.</p></section>',
        '<h2 id="compare">So sánh cùng điều kiện</h2>']
    for warning in comparison.get('warnings', []):
        parts.append('<div class="notice">Cần xem lại: ' + e(warning) + '</div>')
    summaries = []
    for model in models:
        finished = [r for r in ended if r['model'] == model]
        passed = [r for r in finished if r['status'] == 'local_pass']
        summaries.append([model.upper(), f'{len(finished)}/3', len(passed),
                          sum(r['submission_origin'] == 'model' for r in passed),
                          sum(r['submission_origin'] == 'harness' for r in passed),
                          sum(r['status'] == 'incomplete' for r in finished)])
    parts.append(table(['Model','Lượt đã dừng','Local pass','Pass · model nộp','Pass · harness nộp','Chưa hoàn tất'], summaries))
    parts.append('<p>Số pass được đếm trên từng trường hợp A/B/C; các trường hợp có cơ chế khác nhau nên không dùng tổng này để xếp hạng model.</p>')
    matrix = []
    for model in models:
        for ident, label in labels.items():
            selected = [r for r in rows if r['model'] == model and r['experiment'] == ident]
            if not selected:
                matrix.append([model.upper(), label, 'Chờ chạy'] + [None] * 8)
            for r in selected:
                matrix.append([model.upper(), label, r['status'], score(r['evaluation']),
                    round(r['seconds'], 1) if r['seconds'] is not None else None,
                    r['turns'], r['tool_calls'], r['output_tokens'], r['blocked_repeats'],
                    r['submission_origin'], r['stop_reason']])
    parts.append(table(['Model','Cấu hình','Kết quả','Test độc lập','Giây','Lượt','Tools','Output tokens','Lặp chặn','Nguồn nộp','Nguyên nhân dừng'], matrix))
    parts.append('<p>Giây là thời gian giải task, gồm kiểm tra của harness; không gồm chấm patch thu hồi. Khi có nhiều lần chạy, mỗi lần được giữ một hàng riêng.</p><h2 id="details">Chi tiết từng lượt A/B/C</h2><p>Request trùng nguyên văn được đếm theo tên tool và arguments, gồm cả thao tác không chạy do bị chặn; khác bộ đếm lặp của harness.</p>')
    audits = {a['run_id']: a for a in report.get('run_audit', {}).get('runs', [])}
    for r in rows:
        parts.append('<details><summary>' + e(f"{r['model'].upper()} · {labels[r['experiment']]} · {r['status']} · {r['run_id']}") + '</summary>')
        audit = audits.get(r['run_id'])
        if audit:
            parts.append('<p><b>Đánh giá:</b> ' + e(audit['finding']) + '</p>')
            parts.append('<p>Thử submit: ' + e(audit['submit_attempts']) + ' · Request trùng nguyên văn: ' + e(audit['repeated_identical_requests']) + ' · Tool trả lỗi: ' + e(audit['failed_tool_results']) + '</p>')
            for warning in audit['warnings']:
                parts.append('<p class="notice">' + e(warning) + '</p>')
        parts.append('<p>Test độc lập: ' + e(score(r['evaluation'])) + ' · Patch thu hồi (chỉ chẩn đoán): ' + e(score(r['recovered_evaluation'])) + '</p>')
        parts.append('<p>Nguồn nộp: ' + e(r['submission_origin']) + ' · Dừng vì: ' + e(r['stop_reason']) + '</p><p>' + link(r['evidence'], 'Manifest / bằng chứng') + ' · ' + link('runs/' + r['run_id'] + '/', 'Thư mục log và patch') + '</p>')
        parts.append('<p class="muted">Hash điều kiện: <code>' + e(r['control_sha256']) + '</code></p></details>')
    parts.append('<h2 id="history">Các thí nghiệm trước — giữ riêng từng phương pháp</h2>')
    for stage in report['stages']:
        if stage['id'] in labels:
            continue
        parts.append('<section><h3>' + e(stage['id']) + '</h3><p>Trạng thái: ' + e(stage['status']) + ' · Phương pháp: ' + e(stage['mode']) + '</p>')
        records = []
        for r in stage['runs']:
            agent = r.get('agent') or {}
            records.append([r['model'], r.get('workflow_variant'), r['run_id'], r['status'], score(r['evaluation']),
                r.get('elapsed_seconds'), agent.get('reason'), r.get('submission_origin') or ('model' if agent.get('reason') == 'submitted' else None)])
        parts.append(table(['Model','Biến thể','Run','Kết quả','Test','Giây tổng','Nguyên nhân dừng','Nguồn nộp'], records) if records else '<p>Chưa có lượt chạy được lưu.</p>')
        for r in stage['runs']:
            parts.append('<p>' + link(r['evidence'], r['run_id'] + ' · bằng chứng') + '</p>')
        for warning in stage.get('comparison_violations', []):
            parts.append('<p>Cần xem lại: ' + e(warning) + '</p>')
        parts.append('</section>')
    parts.append('<section><h2>Đợt mới: ba lớp cải tiến trên 12B và 31B</h2><p>8 lượt: đối chứng mới, chỉ đổi prompt, chỉ đổi code harness và chỉ đổi cấu hình context runtime. Mỗi nhánh chạy cả hai model; tất cả yêu cầu model tự submit. Cấu hình context runtime tăng giới hạn lịch sử từ 12.000 lên 18.000 ký tự; không đổi vLLM hay GPU.</p><p><b>Phát hiện bổ sung:</b> harness cũ không công nhận python3 tương đương python trong lệnh test. Log 12B B cho thấy test đã pass nhưng vẫn bị giữ ở bước verify. Chưa thể quy toàn bộ lỗi kết thúc cho model.</p><p><a href="../experiments/methods/08-layer-ablation.md">Thiết kế và tiêu chí từng lớp</a> · <a href="two-model-layers.md">Bảng mới</a> · <a href="two-model-layers.json">JSON</a></p></section>')
    layer = report.get('layer_comparison') or {}
    layer_rows = layer.get('rows', [])
    parts.append('<p class="muted">' + e(layer.get('identity_note')) + '</p>')
    parts.append(table(['Model', 'Nhánh', 'Kết quả', 'Tự submit + pass', 'Giây', 'Lượt', 'Tools', 'Dừng vì'],
                       [[r['model'], r['label'], r['status'], r['autonomous_pass'], r['seconds'], r['turns'], r['tool_calls'], r['stop_reason']] for r in layer_rows]))
    if not layer_rows:
        parts.append('<p>Chưa có kết quả đợt mới.</p>')
    for warning in layer.get('warnings', []):
        parts.append('<div class="notice">' + e(warning) + '</div>')
    for assessment in layer.get('assessments', []):
        parts.append('<p><b>' + e(assessment['model'] + ' / ' + assessment['experiment']) + ':</b> ' + e(assessment['finding']) + '</p>')
    for row in layer_rows:
        parts.append('<details><summary>' + e(row['model'] + ' / ' + row['label'] + ' / ' + row['run_id']) + '</summary><p>Test độc lập: ' + e(score(row['evaluation'])) + ' · Patch thu hồi (chẩn đoán): ' + e(score(row['recovered_evaluation'])) + '</p><p>Nguồn nộp: ' + e(row['submission_origin']) + ' · Input tokens: ' + e(row['input_tokens']) + ' · Output tokens: ' + e(row['output_tokens']) + '</p>' + link(row['evidence'], 'Manifest') + '</details>')
    combined = report.get('combined_comparison') or {}
    parts.append('<section><h2>Đợt kết hợp: code mới + prompt mới</h2><p>4 lượt trên URLKit: mỗi model chạy lại code revision 2 với recovery prompt làm đối chứng, rồi revision 2 với completion prompt. Giữ history 12.000 ký tự và ngân sách 900 giây / 48 lượt / 96 tools. Không harness nộp hộ. Một lượt mỗi cấu hình chưa chứng minh tính ổn định hoặc khả năng tổng quát.</p><p><a href="two-model-combined.md">Bảng so sánh</a> · <a href="two-model-combined.json">JSON</a> · <a href="../experiments/methods/09-combined-prompt-code.md">Thiết kế</a></p></section>')
    combined_rows = combined.get('rows', [])
    parts.append(table(['Model', 'Cấu hình', 'Kết quả', 'Tự submit + pass', 'Giây', 'Lượt', 'Tools', 'Dừng vì'],
                       [[r['model'], r['label'], r['status'], r['autonomous_pass'], r['seconds'], r['turns'], r['tool_calls'], r['stop_reason']] for r in combined_rows]))
    if not combined_rows:
        parts.append('<p>Chờ chạy đợt kết hợp.</p>')
    for warning in combined.get('warnings', []):
        parts.append('<div class="notice">' + e(warning) + '</div>')
    for assessment in combined.get('assessments', []):
        parts.append('<p><b>' + e(assessment['model']) + ':</b> ' + e(assessment['finding']) + '</p>')
    for row in combined_rows:
        parts.append('<details><summary>' + e(row['model'] + ' / ' + row['label'] + ' / ' + row['run_id']) + '</summary><p>Test độc lập: ' + e(score(row['evaluation'])) + ' · Patch thu hồi (chẩn đoán): ' + e(score(row['recovered_evaluation'])) + '</p><p>Nguồn nộp: ' + e(row['submission_origin']) + ' · Input tokens: ' + e(row['input_tokens']) + ' · Output tokens: ' + e(row['output_tokens']) + '</p>' + link(row['evidence'], 'Manifest') + '</details>')
    parts.append('<section><h2>Kiểm chứng bằng thư viện harness chính thức</h2><p>Compiler/validator của ban tổ chức và pilot riêng trên issue từ repo thật. Không thay thế điểm Kaggle.</p><p><a href="official/integration-report.html">Mở báo cáo integration và pilot</a></p></section>')
    parts.append('<section><h2>Định nghĩa tiếp theo: đọc repo có mục tiêu</h2><p>R0 đối chứng, R1 prompt đọc có mục tiêu, R2 prompt + ADK skill, trên 12B và 31B. Sáu candidate đã qua compiler; đợt 18 lượt development có bảng trạng thái riêng, không phải holdout hoặc điểm Kaggle.</p><p><a href="reading-v1/definition.html">Xem thiết kế và trạng thái validation</a> · <a href="reading-v1/comparison.html">Kết quả v1 (tràn context)</a> · <a href="reading-v2/comparison.html">Theo dõi v2 context 16k</a></p></section>')
    parts.append('<section><h2>Thử workflow YAML có giới hạn thực thi</h2><p>Nhánh mới: planner → editor/verifier → submitter, skill giới hạn tìm/đọc. Có đối chứng flat mới cho 12B/31B; hàng đợi chờ reading-v2 xong để giữ riêng thí nghiệm.</p><p><a href="staged-v1/comparison.html">Theo dõi staged workflow</a></p></section>')
    parts.append('<section><h2>Thử lại bằng một agent và tool trực tiếp</h2><p>Prompt ngắn, không skill/subagent. Bốn bài chẩn đoán đọc/sửa/ghi/test/submit trước 12 lượt repo thật có đối chứng mới.</p><p><a href="simple-v1/comparison.html">Theo dõi simple direct</a></p></section>')
    parts.append('<section><h2>Kế hoạch đánh giá lại gate:5 phần tách biệt</h2><p>Audit9/9 đã xong:8 skip+1 control đều không có patch pass; FNR among successes chưa xác định. Phần2–5 định nghĩa riêng, hard pruning tắt.</p><p><a href="gate-review-v1/report.html">Đặc tả5 phần, quần thể audit và tiêu chí đánh giá</a></p></section>')
    parts.append('<section><h2>Bước 11: sửa giả thuyết và dự đoán probe mới</h2><p>Một lần revision; hai phép đo mới bị giữ kín trước khi chốt dự đoán.</p><p><a href="revise-hyp-v1/comparison.html">Kết quả trước/sau revision và patch</a></p></section>')
    parts.append('<section><h2>Bước 10: probe trước khi sửa</h2><p>Chốt dự đoán trên code gốc, đo probe, Python lọc giả thuyết; reviewer tách trạng thái giả thuyết và patch.</p><p><a href="role-probes-v1/comparison.html">Bảng probe, ranking và kết quả patch</a></p></section>')
    parts.append('<section><h2>Bước 9: một model, các vai tách biệt</h2><p>Localize, Patch và đọc feedback dùng messages mới; Python giữ/chọn theo test và coverage.</p><p><a href="role-split-v1/comparison.html">Báo cáo vai tách biệt và quyết định của Python</a></p></section>')
    parts.append('<section><h2>Bước 8: so sánh A/B/C</h2><p>Tăng output, chẩn đoán trước edit, và candidate độc lập; từng nhánh lưu riêng.</p><p><a href="repair-strategies-v1/comparison.html">Mở bảng so sánh chiến lược</a></p></section>')
    parts.append('<section><h2>Bước 7: sửa lại sau phản hồi</h2><p>Tối đa hai lần sửa lại mỗi model; phản hồi công khai tách khỏi grader cuối.</p><p><a href="feedback-edit-v1/comparison.html">Theo dõi candidate và kết quả</a></p></section>')
    parts.append('<section><h2>Bước 6: tự suy ra cách sửa từ issue</h2><p>Tách nhánh có và không chỉ dẫn sửa; grader chức năng và hiệu năng đã preflight.</p><p><a href="infer-edit-v1/comparison.html">Bảng so sánh tự suy ra cách sửa</a></p></section>')
    parts.append('<section><h2>Bước 5: context và prompt làm kỹ một phần</h2><p>12 lượt, tách hai yếu tố prompt và độ dài đầu vào trên cả hai model.</p><p><a href="context-prompt-v1/comparison.html">Bảng so sánh từng điều kiện</a></p></section>')
    parts.append('<section><h2>Bước 4: edit một lần với đoạn code chính xác</h2><p>Đối chiếu raw và parsed arguments, thực thi riêng trên repo sạch.</p><p><a href="edit-excerpt-v1/comparison.html">Kết quả kiểm tra edit</a></p></section>')
    parts.append('<section><h2>Bước 3: theo dõi từng bước của 12B và 31B</h2><p>Thí nghiệm riêng trên w3lib_264, chia hiểu yêu cầu, tìm file, đọc, sửa, test và submit. Có điều phối chuyển bước; không gộp với kết quả autonomous.</p><p><a href="stepwise-v1/comparison.html">Mở trace và bảng theo từng bước</a></p></section>')
    parts.append('<section><h2>Bước 2: context dài và skill — tách riêng</h2><p>24 capture trên 12B/31B; ba nhánh độc lập, cùng schema. Context dài là dữ liệu nền tổng hợp; nhánh skill có giao diện khác nên không gộp tỷ lệ thành một kết luận.</p><p><a href="toolcall-stress-v1/comparison.html">Bảng kết quả từng case</a> · <a href="../experiments/methods/14-toolcall-stress-probe.md">Định nghĩa</a></p></section>')
    parts.append('<section><h2>Định nghĩa bước 1: kiểm tra tool-call/parser</h2><p>Bốn case nhỏ trên 12B/31B, đối chiếu raw token và parsed arguments từ cùng lần sinh; không thực thi tool. Trạng thái ở bảng kết quả riêng.</p><p><a href="../experiments/methods/13-toolcall-parser-probe.md">Xem định nghĩa</a> · <a href="toolcall-probe-v1/comparison.html">Kết quả raw/parsed</a></p></section>')
    parts.append('<h2>Vì sao model nhiều tham số vẫn có thể lỗi?</h2>')
    for section in report.get('model_size_analysis', {}).get('sections', []):
        parts.append('<section><h3>' + e(section['title']) + '</h3><p>' + e(section['text']) + '</p></section>')
    metrics_path = root / 'reports/model-comparison.json'
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text())
        parts.append('<h2>Tốc độ sinh · benchmark riêng</h2><p>Benchmark ngắn sau warmup, 3 lần đo với 128 output tokens. Không phải tốc độ toàn task; VRAM là giá trị lấy mẫu.</p>')
        records = []
        for r in metrics.get('rows', []):
            p = r.get('performance') or {}
            records.append([r['model'], p.get('median_end_to_end_tokens_per_second'), p.get('median_ttft_ms'), json.dumps(p.get('sampled_max_memory_mib', {}))])
        parts.append(table(['Model','Tokens/s trung vị','TTFT ms trung vị','VRAM MiB / GPU'], records))
    parts.append('<p>Tài liệu nguồn: <a href="study-report.md">Báo cáo tổng</a> · <a href="anti-loop-comparison.json">Dữ liệu A/B/C JSON</a> · <a href="anti-loop-comparison.csv">CSV</a>. Các lượt lịch sử thay đổi nhiều yếu tố được giữ riêng trong <a href="../experiments/RESULTS.md">chỉ mục kết quả</a>.</p></main></html>')
    target = root / 'reports/study-report.html'
    temporary = target.with_suffix('.html.tmp')
    temporary.write_text('\n'.join(parts), encoding='utf-8')
    temporary.replace(target)
    return target
