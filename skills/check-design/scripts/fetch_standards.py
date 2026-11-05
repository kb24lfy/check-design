#!/usr/bin/env python3
"""Read public GitHub standards at one pinned commit. Stdlib; no tokens or code execution."""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from urllib import request, error, parse

REQUIRED = {'standards/clear.md', 'standards/visual.md', 'standards/visual-tokens.json', 'standards/design-rules.md'}
MAX_FILE = 2 * 1024 * 1024
class FetchError(Exception):
    pass
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def digest(data):
    return hashlib.sha256(data).hexdigest()

def config_read(path):
    data = json.loads(Path(path).read_text())
    if set(data) != {'owner', 'repo', 'ref', 'manifest', 'schema_version'} or data['schema_version'] != 1:
        raise FetchError('不支持的标准源配置。')
    if not all(isinstance(data[k], str) and re.fullmatch(r'[A-Za-z0-9_.-]+', data[k]) for k in ('owner', 'repo')):
        raise FetchError('仓库标识无效。')
    if not isinstance(data['ref'], str) or not data['ref'] or len(data['ref']) > 200:
        raise FetchError('分支/版本无效。')
    if data['manifest'] != 'standards/manifest.json':
        raise FetchError('仅支持 standards/manifest.json。')
    return data

def get(url):
    if not url.startswith('https://api.github.com/repos/'):
        raise FetchError('仅允许 GitHub 官方内容接口。')
    req = request.Request(url, headers={'Accept': ('application/vnd.github.raw+json' if '/contents/' in url else 'application/vnd.github+json'), 'User-Agent': 'check-design-standards/1'})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            result = response.read(MAX_FILE + 1)
    except error.HTTPError as exc:
        raise FetchError(f'GitHub HTTP {exc.code}，未使用旧标准；请检查仓库公开状态、网络或限流。') from None
    except (error.URLError, TimeoutError, OSError):
        raise FetchError('GitHub 读取失败，未使用旧标准。') from None
    if len(result) > MAX_FILE:
        raise FetchError('标准文件超过大小限制。')
    return result

def validate_manifest(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('version'), str):
        raise FetchError('标准清单格式不支持，请更新 Skill。')
    files = data.get('files')
    if not isinstance(files, list) or not 4 <= len(files) <= 16:
        raise FetchError('标准文件清单不完整或过大。')
    paths = set()
    for item in files:
        if not isinstance(item, dict):
            raise FetchError('文件条目格式错误。')
        path = item.get('path', '')
        parts = PurePosixPath(path)
        if (not isinstance(path, str) or '\\' in path or not path.startswith('standards/')
                or '..' in parts.parts or parts.is_absolute() or str(parts) != path
                or parts.suffix not in {'.md', '.json', '.png'} or path in paths
                or not re.fullmatch(r'[0-9a-f]{64}', item.get('sha256', ''))):
            raise FetchError('标准路径或校验值无效，未加载。')
        paths.add(path)
    if not REQUIRED <= paths:
        raise FetchError('缺少三个标准或视觉数值文件。')
    return files

def verify_directory(directory, expected_source):
    lock = json.loads((directory/'snapshot.json').read_text())
    if lock.get('schema_version') != 1 or lock.get('source') != expected_source:
        raise FetchError('本轮快照与标准源不匹配；不要在评审中途混用来源。')
    if not re.fullmatch(r'[0-9a-f]{40,64}', lock.get('commit', '')):
        raise FetchError('快照版本无效。')
    manifest_path = directory/'standards/manifest.json'
    if digest(manifest_path.read_bytes()) != lock.get('manifest_sha256'):
        raise FetchError('本轮清单已改变，请停止判定。')
    manifest = json.loads(manifest_path.read_text())
    for item in validate_manifest(manifest):
        file = directory/item['path']
        if file.is_symlink() or digest(file.read_bytes()) != item['sha256']:
            raise FetchError('本轮标准内容已改变或损坏，请停止判定。')
    return lock

def fetch(source, output, reader=get):
    output = Path(output)
    if output.exists():
        if (output/'snapshot.json').is_file():
            return verify_directory(output, source), 'reused_this_review'
        raise FetchError('输出目录已存在但不是完整快照；请为新评审指定独立空目录。')
    base = f"https://api.github.com/repos/{source['owner']}/{source['repo']}"
    commit_data = json.loads(reader(base+'/commits/'+parse.quote(source['ref'], safe='')))
    sha = commit_data.get('sha', '')
    if not re.fullmatch(r'[0-9a-f]{40,64}', sha):
        raise FetchError('未取得有效提交版本。')
    def content(path):
        return reader(base+'/contents/'+parse.quote(path, safe='/')+'?ref='+sha)
    manifest_bytes = content(source['manifest'])
    manifest = json.loads(manifest_bytes)
    items = validate_manifest(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.standards-', dir=output.parent))
    try:
        (stage/'standards').mkdir()
        (stage/source['manifest']).write_bytes(manifest_bytes)
        resources = []
        for item in items:
            data = content(item['path'])
            if len(data) > MAX_FILE or digest(data) != item['sha256']:
                raise FetchError('标准文件校验失败，未生成可用快照。')
            if item['path'].endswith('.json'):
                parsed = json.loads(data)
                if not isinstance(parsed, dict) or parsed.get('schema_version') != 1:
                    raise FetchError('视觉数值格式不支持。')
            elif item['path'].endswith('.md'):
                if not data.decode('utf-8').strip():
                    raise FetchError('标准正文为空。')
            elif not data.startswith(b'\x89PNG\r\n\x1a\n'):
                raise FetchError('示例图片格式错误。')
            target = stage/item['path']; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            resources.append({'path': item['path'], 'url': f"https://github.com/{source['owner']}/{source['repo']}/blob/{sha}/{item['path']}"})
        lock = {'schema_version':1,'source':source,'commit':sha,'standards_version':manifest['version'],
                'read_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'manifest_sha256':digest(manifest_bytes),'resources':resources}
        (stage/'snapshot.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n')
        verify_directory(stage, source)
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return lock, 'downloaded'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'standards-source.json')
    parser.add_argument('--output',type=Path,required=True,help='本轮评审独立目录；同轮续接复用此目录')
    args=parser.parse_args()
    try:
        lock,status=fetch(config_read(args.source),args.output)
        print(json.dumps({'status':status,'snapshot':str(args.output.resolve()),**lock},ensure_ascii=False,indent=2))
    except (FetchError, ValueError, KeyError, TypeError, OSError) as exc:
        message=str(exc) if isinstance(exc,FetchError) else '标准读取或校验失败；未生成有效快照。'
        print(json.dumps({'status':'blocked','reason':message},ensure_ascii=False));return 1
    return 0
if __name__=='__main__':
    raise SystemExit(main())
