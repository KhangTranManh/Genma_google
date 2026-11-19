"""Verify Gemma tool-call parsing without executing any generated tool."""
import argparse
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/v1')
parser.add_argument('--model', default='gemma-4-e4b-it-qat-w4a16-ct')
parser.add_argument('--output', type=Path, default=Path('runs/smoke-tools.json'))
args = parser.parse_args()
body = {'model': args.model,
        'messages': [{'role': 'user', 'content': 'Read pyproject.toml using the read_file tool. Do not guess its contents.'}],
        'tools': [{'type': 'function', 'function': {
            'name': 'read_file', 'description': 'Read a repository file.',
            'parameters': {'type': 'object', 'properties': {'filepath': {'type': 'string'}}, 'required': ['filepath']}}}],
        'tool_choice': 'auto', 'temperature': 0, 'max_tokens': 256,
        'chat_template_kwargs': {'enable_thinking': False}}
request = urllib.request.Request(args.base_url + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({'request': body, 'response': result}, indent=2) + '\n')
print(json.dumps(result, indent=2))
calls = result['choices'][0]['message'].get('tool_calls', [])
if not calls or calls[0]['function']['name'] != 'read_file':
    raise SystemExit('Expected read_file tool call was not parsed')
arguments = json.loads(calls[0]['function']['arguments'])
if arguments.get('filepath') != 'pyproject.toml':
    raise SystemExit(f'Unexpected arguments: {arguments}')
print('Tool-call parsing passed; no generated command executed.')
