#!/usr/bin/env python3
"""Local macOS setup wizard. No third-party Python packages; no comment writes."""
import argparse
import datetime
import getpass
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent
SERVICE = 'check-design.figma'
ACCOUNT = 'personal-access-token'
RULES = 'https://github.com/kb24lfy/check-design/tree/main/standards'
NORM = 'https://github.com/kb24lfy/check-design/blob/main/standards/visual.md'


def yes(prompt, default=True):
    answer = input(prompt + (' [Y/n] ' if default else ' [y/N] ')).strip().lower()
    return default if not answer else answer in {'y', 'yes', '是'}


def install(destination):
    source = ROOT / 'skills' / 'check-design'
    if not (source / 'SKILL.md').is_file():
        raise RuntimeError('请先完整解压 ZIP，保持 install.py 与 skills 文件夹相邻。')
    if destination.is_symlink():
        raise RuntimeError('目标目录是符号链接，请先人工确认安装位置。')
    if source.resolve() == destination.resolve():
        raise RuntimeError('安装源与目标相同，请从解压目录运行。')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.with_name('check-design.staging-' + str(os.getpid()))
    if stage.exists():
        raise RuntimeError('暂存目录已存在，请检查后重试。')
    shutil.copytree(source, stage, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    backup = None
    try:
        if destination.exists():
            stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            backup = destination.parent.parent / 'check-design-backups' / stamp
            backup.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(backup)
        stage.rename(destination)
    except Exception:
        if backup and backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    print('Skill 已安装：', destination)
    if backup:
        print('旧版已备份：', backup)


def figma_plugins(data):
    # Current Codex list schema groups installed/available records; tolerate nested containers.
    found = []
    def visit(x):
        if isinstance(x, dict):
            ident = x.get('pluginId', '')
            if x.get('name') == 'figma' and re.fullmatch(r'figma@openai-[a-z-]+', ident):
                found.append(x)
            for v in x.values():
                if isinstance(v, (dict, list)):
                    visit(v)
        elif isinstance(x, list):
            for v in x:
                visit(v)
    visit(data)
    return found


def setup_figma():
    cli = shutil.which('codex')
    if not cli:
        print('未发现 Codex CLI。请在 Codex 插件目录搜索 Figma 并安装、连接。')
        return '待完成：在 Codex 内安装/连接官方 Figma 插件'
    try:
        result = subprocess.run([cli, 'plugin', 'list', '--available', '--json'],
                                capture_output=True, text=True, timeout=45)
        candidates = figma_plugins(json.loads(result.stdout)) if result.returncode == 0 else []
    except (ValueError, subprocess.TimeoutExpired):
        candidates = []
    installed = next((x for x in candidates if x.get('installed') and x.get('enabled')), None)
    if installed:
        print('检测到已启用的官方 Figma 插件；这不代表登录或文件访问已验证。')
    else:
        candidate = next(iter(candidates), None)
        if not candidate:
            print('当前 CLI 未提供可识别的官方 Figma 插件，请从 Codex 插件目录安装。')
            return '待完成：在 Codex 内安装/连接官方 Figma 插件'
        if yes('是否安装/启用目录中的官方插件 ' + candidate['pluginId'] + '？'):
            result = subprocess.run([cli, 'plugin', 'add', candidate['pluginId']], timeout=180)
            if result.returncode:
                return '待完成：Figma 插件安装未成功，请从 Codex 内处理'
        else:
            return '待完成：已跳过 Figma 插件安装'
    print('下一步在 Codex 中打开 Figma 插件，点击连接，使用自己的账号完成授权。')
    return '待验证：插件已检测/安装，仍需在 Codex 中完成授权和读取测试'


def save_token(token):
    # Feed security's interactive command over stdin, never put the secret in process argv.
    # Restrict characters so the security command parser cannot interpret token text as commands.
    if not re.fullmatch(r'[A-Za-z0-9_=-]+', token):
        raise RuntimeError('Token 含非预期字符，请确认复制的是 Personal Access Token。')
    command = 'add-generic-password -U -s ' + SERVICE + ' -a ' + ACCOUNT + ' -w "' + token + '"\n'
    subprocess.run(['/usr/bin/security', '-i'], input=command, text=True,
                   capture_output=True, timeout=30)
    result = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', SERVICE,
                             '-a', ACCOUNT, '-w'], capture_output=True, text=True, timeout=30)
    if result.returncode != 0 or result.stdout.strip() != token:
        raise RuntimeError('未能确认钥匙串保存成功，请检查系统授权。')


def setup_token(destination):
    print('\n评论 Token：Figma Settings → Security → Personal access tokens → Generate new token。')
    print('勾选 file_comments:read 和 file_comments:write，设置有效期。不要使用 Plan access token。')
    print('这里只使用对方自己的 Token。输入不回显，保存到本机登录钥匙串。')
    if not yes('是否现在输入/更新本机专用评论 Token？', False):
        return '待完成：评论 Token 未配置，本轮不会读取已有凭据'
    if not sys.stdin.isatty():
        raise RuntimeError('请在终端交互运行，不能通过管道传入 Token。')
    token = getpass.getpass('粘贴 Personal Access Token（不回显；直接回车跳过）：').strip()
    if not token:
        return '待完成：评论 Token 未配置'
    save_token(token)
    status = '已保存：本机钥匙串；评论读写权限尚未全部验证'
    if yes('是否用你自己的目标文件做只读评论接口检查？（不会发评论）'):
        value = input('粘贴 Figma 文件链接或 file key（回车跳过）：').strip()
        match = re.fullmatch(r'https://(?:www\.)?figma\.com/(?:design|file)/([A-Za-z0-9]+)(?:[/?#].*)?', value)
        key = match.group(1) if match else value
        if key and re.fullmatch(r'[A-Za-z0-9]+', key):
            spec = importlib.util.spec_from_file_location('figma_comments', destination/'scripts/figma_comments.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                module.Api(token).comments(key)
                status = '已验证：Token 可读取该文件评论；写权限仍以本人勾选和实际评审发布结果为准'
            except module.ApiError as error:
                status = '待处理：Token 已保存，但评论读取检查失败（HTTP ' + str(error.code) + '）'
        else:
            print('未提供有效文件链接，跳过只读验证。')
    token = ''
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-only', action='store_true', help='只复制 Skill，不读凭据、不访问网络')
    parser.add_argument('--skills-dir', type=Path, help='自定义 skills 目录；默认 CODEX_HOME/skills 或 ~/.codex/skills')
    args = parser.parse_args()
    home = Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))).expanduser()
    destination = (args.skills_dir or home/'skills').expanduser().resolve()/'check-design'
    install(destination)
    if args.install_only:
        print('仅安装模式完成；重开 Codex 聊天后调用 $check-design。')
        return
    if sys.platform != 'darwin':
        print('自动配置向导仅支持 macOS。Skill 已复制；其他系统请参照安装说明手动配置。')
        return
    source_path = destination/'standards-source.json'
    print('\n标准源：kb24lfy/check-design，分支 main；每轮开始固定最新提交版本。')
    if not yes('使用默认公开标准源？'):
        owner=input('GitHub owner：').strip(); repo=input('仓库名：').strip(); ref=input('分支或标签（默认main）：').strip() or 'main'
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',owner) or not re.fullmatch(r'[A-Za-z0-9_.-]+',repo):
            raise RuntimeError('仓库名称无效，Skill已安装，请重新运行配置。')
        source_path.write_text(json.dumps({'schema_version':1,'owner':owner,'repo':repo,'ref':ref,'manifest':'standards/manifest.json'},ensure_ascii=False,indent=2)+'\n')
    figma = setup_figma()
    print('\n飞书：可直接使用 Codex 内置浏览器读取，无需额外安装 lark-cli。')
    print('三个标准来自公开 GitHub，无需飞书规范权限。只需在 Codex 内置浏览器登录并读取自己的 PRD。')
    print(RULES)
    print('公开视觉规范：', NORM)
    if yes('是否在默认浏览器打开公开标准入口？', False):
        webbrowser.open(RULES)
        webbrowser.open(NORM)
        print('默认浏览器登录不代表 Codex 内置浏览器已登录；稍后仍需在 Codex 内验证。')
    token_status = setup_token(destination)
    print('\n配置结果：\n- Skill：已安装\n- Figma：' + figma + '\n- 飞书：待在 Codex 内置浏览器验证正文访问\n- Token：' + token_status)
    if os.environ.get('FIGMA_ACCESS_TOKEN'):
        print('提示：检测到 FIGMA_ACCESS_TOKEN 环境变量，评论脚本会优先使用它；若是旧值，请自行更新或取消。')
    print('\n最后：重开 Codex 聊天，粘贴包内“首次检查提示词.txt”，做只读验收。')
    print('目标设计稿或 PRD 无权限时联系其所有者申请访问；三个公开标准无需额外授权。')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        # Never print subprocess stderr or credential material.
        print('安装/配置未完成：', error if isinstance(error, RuntimeError) else type(error).__name__)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\n已结束。已完成的 Skill 安装会保留，可重新运行继续配置。')
        sys.exit(1)
