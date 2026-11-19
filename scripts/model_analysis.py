"""Evidence-bounded interpretation of the paired local trials."""


def generate(root, comparison, audit):
    rows = (comparison or {}).get('rows', [])
    finished = [r for r in rows if r['status'] not in ('running', 'prepared', None)]
    sections = []
    sections.append(('Phạm vi kết luận',
        f'Đã có {len(finished)}/9 lượt dừng. ' +
        ('Đã đủ chín lượt để tổng kết đợt thử.' if len(finished) == 9 else 'Đây là phân tích tạm thời; đợi các cấu hình còn lại trước khi kết luận.') +
        ' Chỉ một issue và một lần chạy mỗi cấu hình. Chưa xác định quan hệ nhân quả giữa số tham số và tỷ lệ lỗi, chưa đủ kết luận model lớn kém hơn nói chung.'))
    sections.append(('Vì sao nhiều tham số chưa đảm bảo hoàn thành agent',
        'Kết quả đo là cả chuỗi đọc repo → sửa code → kiểm tra → nộp patch. Cần tách khả năng sửa đúng khỏi khả năng gọi tool và kết thúc đúng quy trình. Không submit, patch sai và hết thời gian là những kiểu thất bại khác nhau.'))
    for model in ['31b', '12b', 'e4b']:
        items = [r for r in finished if r['model'] == model]
        if not items:
            continue
        notes = []
        for r in items:
            found = next((a for a in audit['runs'] if a['run_id'] == r['run_id']), {})
            recovered = r.get('recovered_evaluation')
            diagnostic = ('; patch thu hồi pass nhưng không tính thành công' if recovered and recovered['exit_code'] == 0 else '')
            notes.append(f"{r['experiment']}: {r['status']}, dừng={r['stop_reason']}, nguồn nộp={r['submission_origin'] or 'không có'}, "
                         f"request trùng nguyên văn={found.get('repeated_identical_requests', 'chưa đo')}, thử submit={found.get('submit_attempts', 'chưa đo')}{diagnostic} (run {r['run_id']}).")
        sections.append((model.upper() + ' — bằng chứng đã quan sát', ' '.join(notes)))
    if any(r['model'] == '31b' and r['stop_reason'] == 'turn_limit' for r in finished):
        sections.append(('31B: nguyên nhân dừng đã xác nhận',
            'Lượt 31B dừng vì turn_limit đã dùng hết ngân sách lượt. Với lượt đó, không thể quy nguyên nhân dừng trực tiếp cho tốc độ token hoặc thiếu thời gian; cần đọc lỗi edit và chuỗi request lặp trong trajectory. Request lặp là triệu chứng quan sát được, chưa chứng minh cơ chế nội tại gây lặp.'))
    for model in ['e4b', '12b', '31b']:
        baseline = [r for r in finished if r['model'] == model and r['experiment'] == 'progress_baseline_v1']
        guards = [r for r in finished if r['model'] == model and r['experiment'] == 'progress_guard_v1']
        assisted = [r for r in finished if r['model'] == model and r['experiment'] == 'progress_finish_v1']
        if baseline and guards and assisted:
            sections.append((model.upper() + ' — đối chiếu workflow',
                f"A={baseline[-1]['status']}; B={guards[-1]['status']}; C={assisted[-1]['status']}. "
                'A/B thay đổi trạng thái runtime, hướng dẫn động và tập tool cho phép cùng nhau; nếu cải thiện thì chưa tách riêng tác dụng của từng thành phần. '
                'C có thêm harness hỗ trợ nộp và kiểm tra, nên pass ở C không đồng nghĩa model tự submit tốt hơn.'))
    sections.append(('Đính chính nguyên nhân 12B — lỗi harness đã quan sát',
        'Trajectory runs/20261116T071557Z-8c31c62e cho thấy python3 -m unittest discover -s tests -v trả exit 0, '
        'nhưng phase vẫn verify: code cũ so sánh nguyên chuỗi với python -m unittest discover -s tests -v. '
        'Sau đó harness chặn lệnh vì lặp và dừng stalled. Đây là lỗi nhận diện verification của harness, '
        'không đủ cơ sở quy toàn bộ thất bại cho model. Nhánh code v2 công nhận alias interpreter và verbosity tương đương, '
        'vẫn giữ nguyên test target và yêu cầu code version không đổi. Đợt so sánh lớp mới sẽ kiểm chứng tác dụng.'))
    sections.append(('Các giả thuyết chưa được chứng minh',
        'Độ phù hợp giữa model và prompt/tool schema, mất thông tin do compact context, và ảnh hưởng của quantization hoặc cấu hình suy luận có thể góp phần. '
        'Đợt này không thay đổi độc lập các yếu tố đó nên chưa gán lỗi cho chúng. Tốc độ benchmark riêng cũng không giải thích được mọi lỗi task.'))
    sections.append(('Cách xác minh tiếp',
        'Giữ riêng lỗi sửa code, lỗi tool và lỗi kết thúc; chạy lặp trên nhiều issue cố định. Sau đó đổi từng yếu tố: prompt, compact context, tool schema, rồi cấu hình suy luận/quantization nếu đủ tài nguyên. '
        'Đối chiếu trên cùng ngân sách thời gian và thêm phép đo cùng ngân sách lượt/token; không gộp model tự nộp với harness hỗ trợ nộp.'))
    result = {'completed_trials': len(finished), 'sections': [{'title': t, 'text': s} for t, s in sections]}
    path = root / 'reports/model-size-analysis.md'
    temporary = path.with_suffix('.md.tmp')
    temporary.write_text('# Phân tích kích thước model và lỗi workflow\n\n' + '\n\n'.join('## ' + t + '\n\n' + s for t, s in sections) + '\n')
    temporary.replace(path)
    return result
