# check-design

用 CLEAR 法则、视觉规范、设计规则和对应 PRD 检查 Figma 设计，通过 Figma 官方 REST API 在问题位置发布原生评论。

## 安装

下载本仓库 ZIP，完整解压。macOS 双击 `安装.command`，或在仓库目录运行：

```sh
python3 install.py
```

需要 Codex 和 Python 3。安装器复制 `skills/check-design`，备份旧版本，可从当前 Codex 目录安装官方 Figma 插件，并引导本人配置评论 Token。插件登录、目标设计稿与 PRD 权限由使用者本人完成。仅复制：`python3 install.py --install-only`。

详见 [安装和配置说明](安装和配置说明.md)。首次使用粘贴 [首次检查提示词](首次检查提示词.txt) 做只读验收；不要将 Token 发到聊天。

## 使用

```text
$check-design
设计稿：https://www.figma.com/design/你的文件/名称?node-id=你的节点
PRD：对应需求文档链接（可选）
```

- 只有设计：CLEAR、设计检查清单。
- 设计＋PRD：CLEAR、设计检查清单、PRD 与 UI 一致性。
- 只有 PRD：引导补充设计。
- 可指定“只出报告，不评论”。

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
