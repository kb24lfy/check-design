# 安装与配置

此说明用于首次安装、分享和连接排障，不在每次设计检查时加载。

## 安装包入口

完整分享包在 仓库根目录提供 `安装.command`、`install.py`、`安装和配置说明.md` 和 `首次检查提示词.txt`。macOS 用户完整解压后双击 `安装.command`，或在该目录执行 `python3 install.py`。

安装器自动复制 Skill，备份旧版；支持的 Codex CLI 存在时，从当前已配置目录识别并安装官方 Figma 插件。没有 CLI、目录不可用或安装失败时，改为在 Codex 的插件目录搜索 Figma 安装。安装器不下载 Python、Codex 或飞书客户端。

首次登录授权、云端规范/PRD 的访问申请以及创建个人 Token，由接收者本人完成。安装器不迁移分享者凭据，不复制浏览器登录状态。

## Figma

在 Codex 插件目录中找到官方 Figma 插件，安装后点击连接并登录自己的账号。成功安装不代表已授权；授权不代表对所有文件都有权限。首次验收须用当前连接读取自己的目标节点截图和属性，并确认 GitHub 标准完整读取。

## 飞书

不强制安装 lark-cli。已有已授权连接器可优先使用；否则让 Codex 在内置浏览器打开飞书链接，由本人登录。必须看到完整 PRD 正文及表格，而非登录页或预览。默认浏览器、飞书客户端和 Codex 内置浏览器的登录状态可能不同。

本 Skill 的三个标准已迁移到公开 GitHub，按 [标准读取](standards-reading.md) 获取，无需原组织的规范访问权限。接收者仍需拥有自己的目标设计稿和 PRD 权限。

## 评论 Token

Figma 文件浏览器 → 账号菜单 → Settings → Security → Personal access tokens → Generate new token。创建接收者自己的专用 PAT，设置有效期，勾选 `file_comments:read` 和 `file_comments:write`。仅评论不额外要求 `file_content:read`，设计由 Figma 插件读取。PAT 不等于 Figma 插件授权，Plan access token 不支持此评论流程。

macOS 安装器可隐藏输入 Token，写入当前用户钥匙串：service `check-design.figma`，account `personal-access-token`。再次运行可更新；更新同名项前安装器会询问。凭据不会写入 Skill、安装包、命令参数或报告。系统钥匙串授权由本人处理，不要将 Token 发给 Codex 或粘贴进聊天。

评论脚本优先读取 `FIGMA_ACCESS_TOKEN`，其次读取上述钥匙串项。其他系统需要自行在执行环境配置该变量；本安装器不自动持久化其他系统的凭据。Token 到期或撤销后重新配置。删除可在“钥匙串访问”中找到该 service/account 对应项操作。

可用目标文件的评论 GET 接口做只读验证；它只能验证读权限和文件访问，不能证明 write scope。安装器不发布测试评论；首次真实评审时根据 API 返回核验发布能力。

## 首次验收

在 Codex 新聊天中要求：调用 check-design，只做连接检查，不发布评论；读取一个自己的 Figma 节点截图/属性，完整读取 GitHub 三个标准、数值文件和必要示例图，再读取本次 PRD；验证 Token 可读该文件评论。逐项报告成功、失败和未验证，不把安装成功写成授权成功。

之后提供带 node-id 的设计链接和对应 PRD，即可按 Skill 执行 CLEAR、设计检查、PRD 对照和指定状态的评论发布。

## 依据（2026-11-05）

- [Figma 官方连接方式](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)
- [创建 PAT](https://developers.figma.com/docs/rest-api/personal-access-tokens/)
- [Token 权限及文件权限边界](https://developers.figma.com/docs/rest-api/scopes/)
- 插件 CLI 安装语法由当前本机 `codex plugin add --help` 与 `codex plugin list --help` 核对；安装器按接收者目录动态发现插件 ID，不硬编码本机插件缓存路径。
