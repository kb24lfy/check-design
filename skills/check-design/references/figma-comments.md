# Figma 原生评论：REST API

检查结论确定后，通过官方 REST API 发布真实 Comment，定位到问题区域。无需打开或操控 Codex 内置浏览器，不创建标注图层。设计取证继续使用 Figma 连接器；报告按 [报告模板](report-template.md) 交付。

## 发布范围

| 来源 | 允许发布的最终检查状态 |
| --- | --- |
| CLEAR 法则 | 🔴 不符合 |
| 设计检查清单 | 🔴 不符合 |
| PRD 与 UI 一致性 | 🔴 明确不一致、🟠 设计覆盖缺项 |

其他状态均不发布，不为评论而升级待确认或证据不足的问题。本 Skill 检查任务默认包含这些评论，无需逐条再次询问；用户要求只出报告、不要评论或限制范围时优先遵从。仅修改 Skill 不触发线上评论测试。没有可定位的 Figma 文件时，交付有限检查报告并注明无法评论；只有 PRD 时仍先引导补充设计稿。

## 凭据与权限

使用随附 [figma_comments.py](../scripts/figma_comments.py)，仅依赖 Python 3 标准库。它按顺序读取：

1. 进程环境变量 `FIGMA_ACCESS_TOKEN`。
2. macOS 上明确配置的钥匙串通用密码项目：service 为 `check-design.figma`、account 为 `personal-access-token`。仅查这个项目，不遍历其他凭据；钥匙串访问若需要用户授权，遵从系统提示。

脚本支持 Personal Access Token（PAT），使用 `X-Figma-Token` 请求头，只访问 `https://api.figma.com`，不跟随重定向。Token 不得放入聊天、命令参数、JSON 输入、Skill、日志、报告或压缩包，不打印环境变量或钥匙串输出。脚本不创建 Token、不写入钥匙串，不提取浏览器 Cookie 或连接器 OAuth 凭据。

凭据未配置时先完成检查和汇总，明确「评论未完成：未配置 API 凭据」。引导用户在 Figma Settings → Security → Personal access tokens 创建专用 Token，并通过本地安全配置提供；不要求在聊天发送 Token。浏览器登录成功不能替代 API 认证，不自动回退浏览器发布。

- 必需权限：`file_comments:read`（查重、核验）、`file_comments:write`（发布）。账号仍需拥有目标文件的评论权限。
- 只有需要 REST 读取设计节点时才增加 `file_content:read`；连接器已提供位置时不增加。
- 脚本仅支持 PAT；OAuth 需要单独适配，不能当作 PAT 发送。Plan access token 不支持评论写入。
- 不因修改 Skill 自动新增或扩大权限；已有有效授权不重复申请。

## 位置与问题输入

复用本次核验的节点属性、层级和截图，计算设计坐标，不使用浏览器屏幕坐标或导出截图像素直接定位。

- 优先 `FrameOffset`：`node_id` 是承载 Frame 的真实 ID，`node_offset` 是相对其左上角的设计坐标。目标是 Rectangle 或文字时找到承载 Frame，不把任意叶节点当成 Frame。
- 无旋转、缩放时可用问题点画布坐标减去 Frame 原点；有变换时用实际变换矩阵换算。必须核对偏移在 Frame 范围内；位置不可靠则不发布。
- 也支持已核实的画布绝对坐标 `{"x": ..., "y": ...}`。脚本只实现点评论。
- 「设计覆盖缺项」定位到应承载该需求的页面、容器或入口，正文写明补充位置、缺失内容及完整核对范围，不虚构不存在的控件。

### 评论正文格式

- 标题使用 `【CLEAR｜不符合：维度 · 具体问题】`、`【设计检查｜不符合：具体问题】` 或对应 PRD 标题。正文每个字段另起一行，字段名统一用全角 `【】` 包裹，冒号放在括号外，例如 `【当前】：`、`【规范】：`、`【建议】：`、`【复核】：`、`【依据】：`。CLEAR 使用 `【当前】：`、`【依据】：`、`【影响】：`、`【建议】：`；PRD 同样使用 `【需求】：`、`【设计】：`、`【差异】：`、`【建议】：` 等格式。
- 只写适用字段；有历史评论复核事实时才写 `【复核】：`，可保留 `#10` 这样的评论编号。
- 评论已定位到对应位置，标题和正文不展示 `54:4389`、`54-4389` 等裸节点 ID，也不罗列图层 ID。用「日程打卡底板」「排班邀请卡片」等可读名称说明对象；涉及多个位置时用页面、状态和组件名称区分。
- 节点 ID 仍保留在 `client_meta.node_id`、本地证据及发布记录中，供准确定位和查重使用。`【依据】：`中的规范、PRD 链接完整保留，包括链接内必要的 `node-id` 参数。

每条独立问题在本次工作目录创建 JSON，不放入 Skill。下例值均须替换为本次核验数据，`section` 和 `status` 不带 emoji：

```json
{
  "file_key": "已核实的文件或分支key",
  "section": "设计检查清单",
  "status": "不符合",
  "message": "【设计检查｜不符合：具体问题】\n【当前】：实际表现或测量值，以可读名称说明对象。\n【规范】：适用条件与要求。\n【建议】：具体修改方向。\n【依据】：真实规范链接。",
  "client_meta": {"node_id": "123:456", "node_offset": {"x": 12, "y": 24}}
}
```

CLEAR 输入使用 `section: "CLEAR 法则"`、`status: "不符合"`；依据可写 CLEAR 的具体维度及已核验设计事实，不能虚构数值标准或来源链接。

PRD 标题选用 `【PRD 与 UI 一致性｜明确不一致：具体问题】` 或 `【PRD 与 UI 一致性｜设计覆盖缺项：具体问题】`，正文按 `【需求】：`、`【设计】：`、`【差异】：`或`【建议】：`、`【依据】：`分行说明。依据是本地资料时写标题和章节，不发送本机路径或伪造在线地址。不自动 @ 人，不上传完整 PRD 或无关截图。

## 发布、去重与验证

以下脚本路径相对本 Skill 目录；工作文件路径使用本次实际绝对路径：

```sh
python3 scripts/figma_comments.py list --file-key FILE_KEY --output /absolute/work/comments.json
python3 scripts/figma_comments.py post --issue /absolute/work/issue.json --journal /absolute/work/comment-journal.json
python3 scripts/figma_comments.py post --issue /absolute/work/issue.json --journal /absolute/work/comment-journal.json --publish
```

- `list` 只读，保存完整评论列表，控制台只输出数量与路径。先检查相关位置已有讨论；语义相同、仍适用且未解决的问题复用，不仅凭作者或标题查重。不修改、解决或删除他人评论。
- `post` 不带 `--publish` 只校验本地输入和状态，不读 Token、不联网；不证明节点存在或账号有权限。事实、位置和范围确认后，带 `--publish` 直接执行，无需再逐条审批。
- 发送前检查正文字段名已用 `【】` 包裹，且正文未暴露裸节点 ID；不要改动定位参数或依据链接中的节点信息。
- 每条发送前脚本读取评论，自动复用同正文、同位置的未解决根评论；语义近似但措辞不同的去重由评审阶段完成，不能仅因字段格式变化或去掉裸节点 ID 就重复发布。跨三个模块的同一问题合并为一条评论，正文列对应依据；重复场景可在代表位置评论一次，并用可读名称列出受影响页面或组件。
- 顺序执行，同一文件和 journal 不并发写入。整轮评审及中断续跑复用同一 journal，不删除或更换记录来绕过未知状态。新评审可用新记录；已解决问题只有重新核验确实复发才新增。
- 脚本发送前原子保存尝试记录；核验 POST 返回正文与位置后保存真实 `id`、`order_id` 和位置，标记 `published`。`reused`、`already_recorded` 表示已有评论；`recovered` 表示不明确发送后已从列表查证。
- REST 响应没有文档化的评论直链字段。可回填真实评论编号及已核验的节点链接；若已取得并验证本文件的评论 URL 格式，可用真实返回 ID 构造链接，标明未打开验证。不能把 `order_id` 当成全局评论 ID，也不为链接自动启动浏览器。
- 三个模块各为四列表格，第三列回填评论结果，第四列保留真实设计证据截图。API 核验不依赖浏览器效果截图，不生成模拟评论图。

## 失败与恢复

- `400` 检查正文及位置格式；`401/403` 检查 Token 有效期、scope 和账号文件权限；`404` 检查文件或分支 key 与访问权限。API 失败不是设计缺项。
- `429` 遵守 `Retry-After`，脚本输出 `retry_at` 后停止；允许时间之后有限重试，不长时间阻塞或连续调用。
- POST 超时、5xx 或返回不完整时可能已经发送：脚本只读查证一次，匹配则记录 `recovered`，否则保留 `uncertain`，不自动重发。续跑仍先查证；没找到不等于未发送，不能更换 journal 重试发送。
- 全局凭据、权限或连接问题未解决时停止后续发送，交付已完成的汇总表。个别位置有问题则跳过该条，继续其余可核验项。评论受限不改变检查判定，不宣称全部问题已标注。

接口依据（核实日期：2026-11-02）：[评论接口](https://developers.figma.com/docs/rest-api/comments-endpoints/)、[定位类型](https://developers.figma.com/docs/rest-api/comments-property-types/)、[权限](https://developers.figma.com/docs/rest-api/scopes/)、[PAT](https://developers.figma.com/docs/rest-api/personal-access-tokens/)、[限流](https://developers.figma.com/docs/rest-api/rate-limits/)。实际接口行为变化时核对官方文档。
