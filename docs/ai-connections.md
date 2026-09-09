# AI 连接、上下文与隐私

AI 是确定性本地核心之外的可选能力。Catalog、DAG、Grader、事件归约、计时、审查门槛和 mastery 在没有模型时仍然可用。

## 三种模式

| 模式 | 用途 | 是否需要网络或密钥 |
|---|---|---|
| No-AI | 本地课程、测试、复测；个性化模拟面试需要连接 AI | 否 |
| 普通 LLM API | 桌面中的个性化面试、逐轮追问及证据评价 | 视服务而定 |
| Codex | 桌面中的逐问个性化面试与证据评价 | 需要 Codex 可用并完成相应认证 |

适用版本：v1.0.0。首次默认 No-AI；后续启动恢复已保存连接与配置。探测不会发送个人材料，但普通 API 探测可能按服务商规则计费。连接故障不应阻塞本地训练。

## 普通 LLM API

桌面页面把常用配置收敛为：服务、Key 或本地地址、模型、测试连接、保存。Endpoint、显示名称与连接 ID 在高级设置中。

### DeepSeek（当前源码）

打开 **AI 连接 → deepseek**，选择模型和推理强度，输入 API Key，点击 **保存并测试**。无需填写地址，使用官方 `https://api.deepseek.com`。编辑已保存的连接时可以切换模型和推理强度；Key 留空会保留系统密钥环中的原凭证。

- 模型提供 `deepseek-v4-flash`、`deepseek-v4-pro` 与自定义模型 ID；2026-09-07 已通过官方模型列表和真实 `/models` 请求核验，服务端模型会随时间变化。
- 推理选项：关闭思考（默认，更快回复）、低、高、最高、服务默认。关闭对应 `thinking.type=disabled`，其余使用 `enabled` 和 `reasoning_effort=low/high/max`；服务默认不指定强度。支持范围以 [DeepSeek 思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/) 为准。
- 实现读取 SSE 的 `delta.content`，不把 `reasoning_content` 当作回答或评分。面试明确要求结构化结果，因此无论是否思考都设置 `response_format: {type: json_object}`，并提供 JSON 字段说明；只有普通聊天请求不设置。V4 的 [Chat Completion 文档](https://api-docs.deepseek.com/api/create-chat-completion/) 支持该格式，但服务仍可能返回空正文。本地字段、阶段与代码候选校验不放宽，模型和推理强度不自动降级，也不自动重发付费请求。
- “保存并测试”只做关闭思考的短连接检查，不承诺高强度推理的耗时。面试仍使用你保存的模型与强度。`402` 表示余额不足，`401` 表示凭证问题，`429` 表示限流。

2026-09-07 Windows 源码真实验证使用 `deepseek-v4-flash`、关闭思考、合成简历/JD：连续 9 次提交均进入下一问（单轮约 5.45–7.53 秒），随后进入本地中文代码题。代码没有作答，报告如实为未完成；不把这项验证称为完整面试通过。布局和提示词收尾后又验证两轮，分别为 4.52 秒、6.81 秒。这些是该设备和连接的样本，不是服务耗时保证。

v1.0.0 Windows/macOS 包已包含 DeepSeek 接入；下列真实测试属于注明日期的历史证据，本次发布不将其扩展成所有模型与强度均已验收。DeepSeek 聊天接口不作为语音转录服务。

#### 当前真实传输边界（2026-09-08）

统一难度迭代经用户授权，从系统密钥环读取已保存连接，只发送合成简历/JD与合成回答，不读取真实材料。`deepseek-v4-flash/low` 已完成算法岗逐问流程、手撕自测和 10 道已回答题的评分；评分失败项修复并单独重试，没有重评成功项。`high` 后训练场次进入第三问前仍反复出现仅思考无正文，**没有通过整场验收**。详见[执行计划与性能样本](../plans/active/unified-difficulty-interview-workbench.zh.md)。

本轮曾尝试省略思考模式的 JSON Output，但真实模型返回了不能用于冻结下一问的普通文本，因此恢复显式 JSON 要求。不会把思考内容强行当作正文，也不会为了通过而自动换模型、关思考或接受无效题号。失败回答保持锁定，可原位重试；高推理的稳定性仍是剩余风险。

#### 早期空正文审查（历史记录，基线 1075cef）

用户截图对应的操作编号 `3b324c62` 在本地日志中为 `provider_response / INTERVIEW_REQUEST_FAILED`。日志仅记录阶段、类别和操作编号，没有保存原始响应，因此**不能从该日志确认服务那次具体返回了什么，也不能断言是抓错字段**。未读取用户 Profile、材料、录音或 Key。

当时通过官方页面核对：[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/) 支持 V4 Flash 的 `thinking.type=enabled` 与 `reasoning_effort=high`，最终正文仍在 `content`；[JSON Output 文档](https://api-docs.deepseek.com/guides/json_mode) 提示偶尔会返回空正文。这与现象相符，但不是原请求的完整根因证明。当时省略思考模式 `response_format` 的尝试已被上方新实现取代；始终未将思考片段用作答案。

本次审查修复的直接问题：

- SSE 内的 `error` 原先会被忽略，最后只提示没有正文；现在显示已知错误码及下一步，不回显可能含凭证或 Prompt 的服务原文。
- 只有空白的 `content` 原先被当成有正文；现在与「仅返回思考」「输出预算用完」「过滤」「服务资源不足」分别提示。
- DeepSeek 流在没有正常终止标记时结束，不再产生 `completed`；不保存半截题目或评分。
- 普通 API 原先只有单次 HTTP 读取超时，保活/思考包可能不断重置等待；现在整轮最多 180 秒，超时关闭本次传输并解除 busy，回答继续保留。
- 动态面试失败后可以直接重试，不再同时出现要求先跳去连接页测试的矛盾提示。

实际验证（基线 `1075cef`）：

- `test_deepseek.py` 与 `test_ai_connections.py`：38 passed，覆盖 none/low/high/max/服务默认的请求、思考与最终文本分离、SSE 失败、连接关闭及原兼容服务。
- `test_interview_input_runtime.py -k deepseek_high_real_adapter`：1 passed。使用正式 Windows QML、真实 Controller、HTTP/SSE 适配器和隔离档案；Keyring 和网络响应为测试替身。实际点击一次失败，再点击重试到 q-002，提交下一次回答到 q-003；每次都保留 V4 Flash/high，失败回答不重写、不重复评分。最终直接复验耗时 8.65 秒。
- 同文件 `-k provider_deadline`：1 passed。模拟持续保活流，验证超时取消、连接操作释放、原回答和未评分状态保留。
- 故障用例先在旧实现下失败，再修复并通过。新 QML 测试曾因合成证据不足 20 字、未等下一帧的编辑器清空而失败；修正测试数据和事件循环等待后通过，没有降低产品校验。

这批早期失败重试与第三问截图位于 ignored `workspace/maintainer/agent-runs/deepseek-high-20260908/`，状态和问句是模拟服务结果，不证明真实账户成功。当时未调用付费 API；后续经授权的真实结果见上方“当前真实传输边界”。两批验证都没有运行全量 pytest、CI、打包或发布，不能声称服务端空响应已消除。

使用当前源码重启，继续原来的面试，点击「重试生成下一问」即可检验；无需重填 Key、关闭高强度或重建档案。已锁定回答会继续使用。

打包桌面重点验证：

- OpenAI；
- OpenAI-compatible；
- Ollama `/v1`。

源码安装的统一 Provider 层还支持 Anthropic 与 Gemini。语音默认使用 [Zipformer 本地流式预览，Qwen3-ASR 0.6B 停句校准](local-stt.md)，权重单独下载后在本机运行，SenseVoice 已移除。可选远程转录仍在停录后走 OpenAI / OpenAI-compatible 的 `/audio/transcriptions` 接口，需单次授权；语音只是回答草稿工具，不会自动提交或评分。Embedding、图像生成、RAG、MCP Runtime 与 Tool Marketplace 不在本版本范围内。

### 安装

```bash
python -m pip install -e ".[ai]"
```

Python 3.11 是统一 Provider 可选依赖的推荐版本。

### 常见错误

#### 面试中「仅返回思考」或其他响应失败（2026-09-09 源码）

回答区的错误提示下方新增 **复制脱敏诊断**，不必寻找整份日志或重新填写 Key。复制不会发起 API 请求；只有点击「重试生成下一问」才再次发送已保存回答及当前授权范围。模型、推理强度、JSON 输出要求和本地题目校验保持不变，不自动增加付费重试。

诊断记录服务、公开 DeepSeek 模型 ID、推理设置、HTTP 状态、可识别的服务请求/响应 ID、结束原因、是否收到 `[DONE]`、思考/正文字符数、首次有效正文与总耗时，以及服务实际提供的 token 用量。字符数不是 token 数；缺失的结束原因/用量保持未知，不推测为正常结束或零消费。自定义模型名称不复制，未识别的 ID 不原样导出。

| 错误码 | 含义 |
|---|---|
| `AI_RESPONSE_REASONING_ONLY` / `AI_RESPONSE_EMPTY` | 流已终止，但只有思考或空白，没有有效正文 |
| `AI_RESPONSE_TRUNCATED` | 服务报告输出预算耗尽；不保存半截题目 |
| `AI_RESPONSE_INTERRUPTED` | 未收到正常终止标记，连接已结束 |
| `AI_RESPONSE_UNEXPECTED_FINISH` | 服务以非预期原因结束，不能确认可用回答 |
| `AI_REQUEST_TIMEOUT` | 等待超时；诊断区分 HTTP 读取等超时与整轮 180 秒截止 |
| `AI_HTTP_ERROR` / `AI_PROVIDER_ERROR` | HTTP 拒绝请求或流内服务错误；保留已知状态码，不导出服务错误原文 |

不复制 Key、地址、个人路径、简历/JD、用户回答、模型正文或思考正文。失败元数据也写入现有本地日志的 `interview_provider_failure`，用 `operation_id` 对应页面编号；后台评分失败只记日志，不打断正在作答的场次。

这项改动改善排查，并修正未知结束原因可能被当成正常完成的问题；**不代表 DeepSeek 的空回复已经消除**。官方 [JSON Output 说明](https://api-docs.deepseek.com/guides/json_mode/) 提到可能出现空正文，具体失败仍需依据当次元数据判断。无需为了排查上传原始响应或个人材料。

#### 连接保存与测试失败

源码预发布版 `1.0.1a1` 新增「复制脱敏诊断」。连接失败时请复制这段信息反馈，不要发送 API Key 或完整日志。内容仅包括应用版本、系统、失败阶段、固定错误码、HTTP 状态、异常类型及操作编号；401、DNS、证书、代理、超时和本地密钥环故障可分别定位。初始化失败会明确说明请求尚未发送；Key 写入后读回失败不再显示保存成功。已有 v1.0.0 包尚无此功能；本轮[从源码运行](desktop-app.md#源码运行)，不要求下载新包。

- `401`：检查系统密钥环中的 Key；
- `429`：等待限流窗口，减少重试频率；
- `500 / 502 / 503`：服务临时错误，稍后重试；
- Timeout：检查网络、Endpoint 和本地服务；
- Ollama 未启动：启动 Ollama，再测试 `http://127.0.0.1:11434`；
- Keyring 不可用：不会回退到明文文件，继续使用 No-AI。

界面日志只记录经过清理的错误类别，不记录 Authorization Header、Key 或完整 Prompt。

### 面试语音转录（可选）

非代码面试点击「语音输入」开始本地录音，点击「完成录音」自动转成文字。录音保存在当前学习档案的面试目录；默认本地识别，不上传音频。只有在「语音设置」选择可用的 OpenAI / OpenAI-compatible 转录服务并明确授权这次远程发送，音频才会发送。结果追加到可编辑草稿，仍需检查、修改并点击「提交并继续」。

没有麦克风、转录服务不可用、网络中断或不愿发送音频时，直接使用文字回答即可。应用不会把音频写入 Profile YAML、事件日志或普通配置，也不会因为转录失败阻塞 No-AI 训练。

## 上下文预览

远程请求默认只允许包含：

- 当前公开题面；
- 用户主动选择的当前答案；
- 最近一次公开测试摘要；
- 当前岗位与 Skill；
- 本场难度与已发生的问答；
- 面试行为规则与所选知识候选的追问路线。

默认排除：整个 Workspace、其他学习档案、其他场次答案、Git 历史、雇主材料、Oracle、Private Tests、API Key 和未授权材料。本场主动提交的历史问答用于连续追问；结束评分逐题发送，不重评成功项。

预览会显示每个部分、是否敏感、选择状态、预计 token 和适用时的 SHA-256。取消对话框不会发送任何内容。降低 token 的推荐做法：只发送当前题、必要错误摘要和最小答案片段，不发送完整日志或无关材料。

## 求职材料授权

材料是 **不可信证据**，不是指令。材料中的命令、Prompt Injection、链接或“读取其他文件”等文字不会改变应用规则。

用于面试前必须逐场确认：

1. material ID；
2. 用途；
3. 当前 SHA-256；
4. 明确同意。

文件变化会让旧 SHA 与授权失效。不得上传公司源码、内部数据、未公开指标、配置、日志、截图或保密文档。

文本型 PDF 与 DOCX 在导入时可生成 SHA-256 绑定的只读文本快照（PDF 不做扫描件 OCR；DOCX 提取段落和表格）。只有快照存在且原文件 SHA 未变化时，才会出现在上下文预览中。无法提取的文件仍可仅保存在本机，但不能勾选 AI 使用。

## API Key

Key 只写入操作系统密钥环：

- Windows：Credential Manager；
- macOS：Keychain；
- Linux：由已配置的 keyring backend 决定。

普通配置只保存：`provider_id`、`base_url`、`model`、`display_name` 与不敏感的 `key_reference`。学习事件、Profile YAML、日志、截图和 Release Artifact 都不能包含 Key。

保存、读取、应用重启后读取和删除均通过同一 Keyring 接口。若 Keychain / Credential Manager 拒绝访问，应用会明确报错，不会创建明文后备文件。

## Codex 集成

桌面版使用官方 Codex App Server JSONL 协议，不解析交互式终端 ANSI 输出，也不模拟键盘输入。

当前支持：

- `initialize / initialized`；
- account 状态；
- Thread 创建与恢复；
- Turn 与流式事件；
- Cancel / Retry；
- 文件 Diff；
- 命令与文件写入审批；
- Interviewer 面试官模式。

桌面端只保留面试官，不再提供 AI 辅助页、练习教练或仓库代理入口；面试官不修改答案。历史 CLI 能力与本地教练记录保留兼容，不删除用户数据。

在桌面端“设置 → 模型与推理强度”中可以为 Codex 选择模型 ID 和 `default / low / medium / high / xhigh` 推理强度。该设置用于面试评估和动态面试的下一问；只影响新的 Codex 请求。面试设置页选择“Codex”后也会显示当前值并提供“修改”入口。动态面试在用户确认上下文后创建会话，不会预先生成整场问题。

同一场面试、模型和材料/背景授权快照不变时，应用复用同一 App Server Thread，通过新的 `turn/start` 继续。换档、换场、换模型、取消材料或 SHA 变化时，使用新 Thread 隔离旧上下文；本地 Session 仍是学习记录的事实源。这与 [Codex App Server 的 Thread / Turn 协议](https://learn.chatgpt.com/docs/app-server) 对齐，不是每次启动一个 Codex CLI。

“已连接”表示本地 App Server 可用，不保证上游模型网络畅通。`responseStreamDisconnected / request timed out / Reconnecting` 属于上游传输失败，不是用户需要再次手动连接。客户端、账户、模型、强度和上下文不同，不能用另一个聊天窗口保证本应用速度。新面试流式显示下一问正文，标注生成中；完整校验后才冻结并允许回答，不展示思考、JSON 或中途评分。实际冷启动遇到过约两分钟的上游重连，后续暖请求较快；样本见执行计划，不作秒级保证。

### macOS 查找 Codex

Finder 启动的 `.app` 不保证继承登录 Shell 的 PATH。应用依次检查：

- 用户在设置中选择的路径；
- 当前 PATH；
- `/opt/homebrew/bin/codex`；
- `/usr/local/bin/codex`；
- 常见的 `.local`、npm、Volta 与 Bun 用户目录。

设置中只保存非敏感可执行文件路径。未检测到或未登录时，No-AI 和普通 API 继续可用。

### 历史协议能力：操作审批

App Server 适配层保留下列审批表达，用于旧协议兼容；当前桌面只提供面试官，不将其作为仓库代理功能宣传，也不允许面试官替用户写答案：

```text
操作
范围
文件
命令
原因
风险
Diff
仅批准本次 / 拒绝
```

应用不会自动批准全部写操作。默认不允许读取 Oracle、其他学习档案或修改个人 Submission。

## AI 行为边界

桌面 AI 只围绕面试流程、目标岗位、获准背景和实际回答进行追问与评估，不在练习页提供教学或代写。H0–H5 等旧 CLI 规则仍见 Policy，不作为桌面可点击能力宣传。

AI 不能自行：

- 在 Reviewer 模式替学习者修改答案；
- 用一次测试通过授予 mastery；
- 修改固定 DAG；
- 把生成题自动加入公共题库；
- 把公开测试说成防作弊隐藏测试；
- 上传本地学习档案；
- 证明恶意代码安全；
- 代替 Oracle、契约审查或间隔复测。

详细模式见 [`coach/POLICY.md`](../coach/POLICY.md)。

## 测试边界

CI 只使用 Fake Provider、Fake Codex 与 Mock Keyring，覆盖流式响应、取消、Timeout、401、429、500、无效模型、上下文预览、缺少 Key、审批、Diff 和错误恢复。CI 不调用真实付费 API、真实 Codex 账号或真实系统密钥环。
