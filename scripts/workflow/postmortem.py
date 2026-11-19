"""Evidence-based completed-run analysis; no model calls or candidate edits."""
from pathlib import Path
from collections import Counter
from html import escape
import json
import re
ROOT=Path(__file__).resolve().parents[2]


def generate():
    records=[]
    for model in ['31b','12b']:
        for task in ['w3lib_264','packaging_1125','platformdirs_540']:
            folder=ROOT/'runs/staged-v1'/model/'staged'/task
            trace=json.loads(next((folder/'traces').glob('*.json')).read_text())
            counts=Counter();errors=Counter();missing_paths=0;invalid_skill=0;test_runs=[]
            for step in trace['steps']:
                calls=step.get('tool_calls',[])
                for call in calls:
                    name=call.get('function_name');counts[name]+=1;args=call.get('arguments') or {}
                    if name=='write_file' and isinstance(args,dict) and not args.get('filepath'):missing_paths+=1
                try:result=json.loads((step.get('observation') or {}).get('content',''))
                except (ValueError,TypeError):continue
                if not isinstance(result,dict):continue
                if result.get('error_type'):errors[result['error_type']]+=1
                if result.get('error_code')=='INVALID_ARGUMENTS':invalid_skill+=1
                if isinstance(result.get('stdout'),str):
                    try:inner=json.loads(result['stdout'])
                    except ValueError:continue
                    if isinstance(inner,dict) and 'exit_code' in inner:
                        test_runs.append({'exit_code':inner['exit_code'],'summary':re.findall(r'\d+ (?:passed|failed|errors?)',inner.get('output',''))[-3:]})
            patch=(folder/'agent.patch').read_text();summary=json.loads((folder/'summary.json').read_text())
            records.append({'model':model,'task':task,'tool_requests':dict(counts),'tool_error_types':dict(errors),
                            'missing_filepath_requests':missing_paths,'invalid_skill_arguments':invalid_skill,
                            'patch_files':re.findall(r'^diff --git a/(.*?) b/',patch,re.M),
                            'local_script_test_runs':test_runs,'resolved':summary.get('resolved'),
                            'independent_test_summary':re.findall(r'\d+ (?:passed|failed|errors?)',summary.get('test_output',''))[-3:],
                            'evidence':str((folder/'summary.json').relative_to(ROOT))})
    findings=[
        ('12B: hành động thiếu quan sát và lặp lỗi edit', 'Cả ba lượt staged không có load_skill/run_skill_script. Do đã bỏ read_file và run_command trực tiếp, model không đọc source bằng interface mới mà thử edit. Packaging có 45 edit_file requests, 42 FileEditError; w3lib có 11 write_file requests đều thiếu filepath. Platformdirs có 7 edit failures rồi 40 write_file requests, patch source cuối không có thay đổi. Đây là lỗi tương tác tool và phục hồi, không phải bằng chứng riêng về năng lực lập trình.'),
        ('31B: interface skill phức tạp và sửa quá hẹp', 'Packaging có 42 run_skill_script requests và 37 INVALID_ARGUMENTS, chủ yếu thiếu skill_name hoặc ghép field vào file_path. W3lib có 11 FileEditError và chỉ còn file tái hiện lỗi trong patch. Platformdirs tới được submitter, sửa source và pass 3 test tự viết, nhưng chấm độc lập vẫn 61 fail / 748 pass: patch chưa bao phủ đầy đủ hành vi cần kiểm chứng.'),
        ('Workflow của chúng ta cũng góp phần', '12B mất tool đọc quen thuộc nhưng không chuyển sang skill. Interface yêu cầu skill_name + file_path + args lồng nhau làm tăng cơ hội gọi sai. Script hard-cap chặn inspection, nhưng không chặn lặp edit sai hoặc buộc editor kết thúc; 5/6 lượt không qua editor. Compiler pass và fixture tests chỉ chứng minh cơ chế, không chứng minh phù hợp với model thật.'),
        ('Chưa xác định nguyên nhân gốc ở weights hay parser', 'Trace lưu arguments đã qua parser. Chưa có phép đối chiếu raw model output với parser hoặc ablation riêng cho compaction/template. Do đó chưa quy lỗi cho quantization, tham số, training hoặc vLLM parser. Cần kiểm thử tool-call trên fixture có đáp án biết trước, tách khỏi bài sửa repo.'),
        ('Ưu tiên tiếp theo', 'Đo và đơn giản hóa giao diện tool trước khi thêm agent. Kiểm tra các ca read/edit/write có schema tối giản; xác nhận raw output và arguments parsed; chạy sửa file nhỏ có kiểm chứng. Sau khi model dùng tool ổn định mới thử lại workflow staged, với editor có cách đọc source đáng tin và cơ chế handoff có thể kiểm chứng. Chưa nên tăng budget hoặc fine-tune từ sáu lượt này.')]
    output=ROOT/'reports/staged-v1'
    (output/'postmortem.json').write_text(json.dumps({'scope':'Six staged development runs; descriptive evidence, not model-wide causal conclusions.','runs':records,'findings':[{'title':t,'text':v} for t,v in findings]},indent=2,ensure_ascii=False)+'\n')
    lines=['# Phân tích thất bại của staged workflow','','Sáu lượt development, không phải kết luận tổng quát về model.','']
    for title,text in findings:lines+=['## '+title,'',text,'']
    (output/'postmortem.md').write_text('\n'.join(lines))
    html=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Staged postmortem</title><style>body{font:16px/1.7 system-ui;max-width:1000px;margin:30px auto;padding:0 20px;color:#18314b}section{padding:15px;background:#f3f6fa;margin:15px 0}pre{white-space:pre-wrap}</style><h1>Model bị gì trong thử nghiệm staged?</h1><p>Điểm nghẽn quan sát được: dùng tool, phục hồi lỗi và handoff; chưa đủ kết luận model không có năng lực sửa code.</p>']
    for title,text in findings:html.append('<section><h2>'+escape(title)+'</h2><p>'+escape(text)+'</p></section>')
    for r in records:html.append('<details><summary>'+escape(r['model']+' / '+r['task'])+'</summary><pre>'+escape(json.dumps(r,indent=2,ensure_ascii=False))+'</pre></details>')
    html.append('<p><a href="comparison.html">Bảng kết quả</a> · <a href="postmortem.json">Dữ liệu phân tích</a></p></html>')
    (output/'postmortem.html').write_text('\n'.join(html))

if __name__=='__main__':generate()
