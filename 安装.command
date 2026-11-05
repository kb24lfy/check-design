#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  print '未找到 Python 3。请先从 https://www.python.org/downloads/macos/ 安装，再运行本文件。'
else
  python3 install.py
fi
print '\n按回车关闭窗口。'
read
