"""Download an exact public Hugging Face snapshot; no credentials required."""
import argparse
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--repo', required=True)
parser.add_argument('--revision', required=True)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
url = f'https://huggingface.co/api/models/{args.repo}/revision/{args.revision}'
with urllib.request.urlopen(url, timeout=60) as response:
    info = json.load(response)
args.output.mkdir(parents=True, exist_ok=True)
for item in info['siblings']:
    name = item['rfilename']
    if name.startswith('.') or name == 'README.md':
        continue
    path = args.output / name
    if '..' in Path(name).parts or Path(name).is_absolute():
        raise ValueError(f'Unsafe filename: {name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    print(f'Downloading {name}', flush=True)
    with urllib.request.urlopen(f'https://huggingface.co/{args.repo}/resolve/{args.revision}/{name}', timeout=120) as source:
        expected = source.headers.get('Content-Length')
        count = 0
        with temporary.open('wb') as target:
            while chunk := source.read(8 * 1024 * 1024):
                target.write(chunk)
                count += len(chunk)
        if expected and count != int(expected):
            raise ValueError(f'Incomplete download: {name}')
    temporary.replace(path)
    print(f'Finished {name}: {count:,} bytes', flush=True)
(args.output / 'source.json').write_text(json.dumps({'repo': args.repo, 'revision': info['sha']}, indent=2) + '\n')
