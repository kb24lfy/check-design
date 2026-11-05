# check-design

用 CLEAR 法则、视觉规范、设计规则和对应 PRD 检查 Figma 设计，通过 Figma 官方 REST API 在问题位置发布原生评论。

## 第一次使用：把这段话发给 Codex

复制以下提示词到 Codex 聊天，即可让 Codex 协助下载和安装：

```text
请从 https://github.com/kb24lfy/check-design 安装 check-design Skill，
按仓库说明检查安装位置，并引导我完成 Figma 连接、PRD 访问和可选的评论 Token 配置。
安装后用我提供的设计稿链接做一次只读验收，不发布评论；需要登录授权时让我本人操作。
```

### 首次配置

1. **连接 Figma（必需）**：在 Codex 安装并连接官方 Figma 插件，用自己的账号完成授权，确认能读取要检查的设计稿。
2. **访问飞书 PRD（按需）**：只检查设计稿可跳过。需要核对 PRD 时，用本人账号登录 Codex 内置浏览器，确认能看到对应文档正文。
3. **配置 Figma 评论 Token（按需）**：只看报告可跳过。需要自动评论时，在 Figma 的 **Settings → Security → Personal access tokens** 创建个人 Token，勾选 `file_comments:read` 和 `file_comments:write`，并确认账号有目标文件的评论权限。macOS 安装向导可通过隐藏输入将 Token 保存到本机钥匙串；**不要把 Token 发到聊天里**。
4. **做一次只读验收**：新开 Codex 聊天，使用 [首次检查提示词](首次检查提示词.txt)，填入自己的设计稿和可选 PRD 链接，确认能读取设计与公开标准。读取公开标准无需 GitHub 登录或 Token。

### 也可以手动安装

下载 [最新安装包](https://github.com/kb24lfy/check-design/releases/latest)，完整解压。macOS 双击 `安装.command`，或在解压目录运行：

```sh
python3 install.py
```

需要 Codex 和 Python 3。安装器复制 `skills/check-design`，备份旧版本，可从当前 Codex 目录安装官方 Figma 插件，并引导本人配置评论 Token。插件登录、目标设计稿与 PRD 权限由使用者本人完成。仅复制：`python3 install.py --install-only`。

详见 [安装和配置说明](安装和配置说明.md)。

## 开始检查

```text
$check-design
设计稿：https://www.figma.com/design/你的文件/名称?node-id=你的节点
PRD：对应需求文档链接（可选）
本次只出报告，不评论。
```

- 只有设计：CLEAR、设计检查清单。
- 设计＋PRD：CLEAR、设计检查清单、PRD 与 UI 一致性。
- 只有 PRD：引导补充设计。
- 想自动发布符合条件的问题评论时，先完成 Token 配置，再去掉示例中的“只出报告，不评论”。

三个部分分别一张四列表格，最后一列是真实截图。

| 部分 | 四列 | 自动评论范围 |
| --- | --- | --- |
| CLEAR | 状态／维度／分析、依据与建议／局部截图 | 不符合 |
| 设计检查清单 | 状态／检查项／说明／局部截图 | 不符合 |
| PRD 与 UI 一致性 | 状态／检查项／对照说明／局部截图 | 明确不一致、设计覆盖缺项 |

CLEAR 先符合、后不符合，未判定最后；同状态按 C、L、E、A、R。评论通过官方 REST API，字段使用【当前】【依据】【建议】等格式，不展示裸节点 ID。跨模块同一问题复用一条评论，已有同问题讨论先查重。运行时权限、算法和业务计算不能仅凭静态稿判错。

## 三个云端标准

- [CLEAR 法则](standards/clear.md)
- [视觉规范](standards/visual.md) 与 [精确数值](standards/visual-tokens.json)
- [设计规则](standards/design-rules.md)

每轮新评审查询 main 最新提交，按同一提交完整下载清单中的内容和必要示例图，校验成功后固定版本。本轮续接复用，下一轮重新读取。报告在原来源说明位置记录标准版本、完整提交 SHA 和读取时间；报告表格与评论程序不随云端标准内容更新而改变。

脚本手动检查示例：

```sh
python3 skills/check-design/scripts/fetch_standards.py --output /你的评审目录/standards-snapshot
```

默认源见 `skills/check-design/standards-source.json`。读取公开标准不需要 GitHub Token；当前脚本只支持公开仓库。远端标准作为评审数据读取，不执行其中的程序，也不自动更新本机 Skill。网络/校验失败会明确停止依赖该来源的判定，不冒用旧版。

原 Figma 和飞书规范保留为出处。迁移后需要在本仓库维护标准；原出处后续更改不会自动同步。来源冲突和既有暂缓项均保留，详见标准正文。

## 修改标准与更新 Skill

1. 编辑 standards 下相应文件，保持规则原意、条件、例外和编号。
2. 如果改变文件或示例图，执行 `python3 tools/update_manifest.py` 更新 SHA256 清单。
3. 执行 `python3 -m unittest discover -s tests -v`。
4. 提交并合并到 main，下一轮评审读取新版本。标准版本号可在 manifest.json 中更新。
5. 仅标准内容变化不要求重装 Skill；Skill 流程、安装器或脚本升级时重新安装。可将 ZIP 和更新说明发布到 GitHub Releases。

开源包不包含任何真实 PRD、评审记录、目标设计截图或个人 Token。规范来源与迁移信息见 [来源说明](SOURCES.md)。
