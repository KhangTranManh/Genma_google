"""Reviewable definition report; never executes model jobs."""
from pathlib import Path
from html import escape
import json
import tomllib
ROOT=Path(__file__).resolve().parents[2]


def generate(root=ROOT):
    plan=tomllib.loads((root/'configs/reading-study.toml').read_text())
    folder=root/'reports/reading-v1';folder.mkdir(parents=True,exist_ok=True)
    definition=json.loads((folder/'definition.json').read_text())
    for row in definition['candidates']:
        path=folder/row['arm']/f"{row['model']}-validation.json"
        row['compiler_validated']=json.loads(path.read_text()).get('agent_compiled',False) if path.exists() else False
    (folder/'definition.json').write_text(json.dumps(definition,indent=2)+'\n')
    labels={'baseline':'R0 · Đối chứng','prompt':'R1 · Prompt đọc có mục tiêu','skill':'R2 · Prompt + ADK skill'}
    state_path=root/'runs/reading-v1/state.json'
    started=state_path.exists()
    rows=''.join('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in [r['model'],labels[r['arm']],r['compiler_validated'],'Xem bảng thực thi' if started else 'Chưa chạy'])+'</tr>' for r in definition['candidates'])
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Định nghĩa focused reading</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#17304d}table{border-collapse:collapse;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;background:#f2f5fa;padding:20px}.note{padding:15px;background:#edf3fa}</style><h1>Định nghĩa: đọc repo có mục tiêu</h1><p class="note">Đã định nghĩa và kiểm tra compiler; chưa chạy model, chưa cài trigger đợt này.</p><p>18 lượt development dự kiến: 2 model × 3 nhánh × 3 issue đã xem. Không phải holdout hoặc điểm Kaggle.</p><table><tr><th>Model</th><th>Nhánh</th><th>Compiler pass</th><th>Model evaluation</th></tr>'''+rows+'''</table><h2>Điều kiện cải thiện</h2><p>Model tự submit và pass test độc lập. Sau đó mới so số lần đọc lặp, lỗi arguments, thời gian tới edit đầu, lượt/tool calls, tokens và thời gian tổng. Ít read hơn nhưng patch sai không phải cải thiện.</p><p>Giữ 48 lượt / 96 tools / 15 phút; không thay runtime hay auto-submit. Checkpoint sau bốn inspection là hướng dẫn mềm, không chặn tool. Skill không có script hoặc host callback.</p><h2>Quy trình trong prompt</h2><pre>'''+escape((root/'experiments/prompts/focused_reading_v1.md').read_text())+'''</pre><p><a href="../../experiments/methods/10-focused-reading.md">Thiết kế đầy đủ</a> · <a href="../../configs/reading-study.toml">Plan TOML</a> · <a href="definition.json">Candidate JSON</a> · <a href="../study-report.html">Báo cáo tổng</a></p></html>'''
    if started:
        html=html.replace('Đã định nghĩa và kiểm tra compiler; chưa chạy model, chưa cài trigger đợt này.', 'Đã định nghĩa và kiểm tra compiler; đợt thực thi đã được khởi tạo. Xem trạng thái mới nhất ở bảng theo dõi.')
    html=html.replace('<h2>Điều kiện cải thiện</h2>', '<p><a href="comparison.html">Mở bảng theo dõi thực thi R0/R1/R2</a></p><h2>Điều kiện cải thiện</h2>')
    (folder/'definition.html').write_text(html)
    return definition


if __name__=='__main__':
    generate();print(ROOT/'reports/reading-v1/definition.html')
