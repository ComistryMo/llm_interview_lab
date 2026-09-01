# AI 连接、上下文与隐私

AI 是确定性本地核心之外的可选能力。Catalog、DAG、Grader、事件归约、计时、审查门槛和 mastery 在没有模型时仍然可用。

## 三种模式

| 模式 | 用途 | 是否需要网络或密钥 |
|---|---|---|
| No-AI | 课程、测试、复测、手动模拟面试 | 否 |
| 普通 LLM API | 解释、提示、只读审查、面试追问 | 视服务而定 |
| Codex | 仓库感知教练、个性化面试计划、测试、Diff 与受审批维护 | 需要 Codex 可用并完成相应认证 |

首次启动默认选择 No-AI。任何连接故障都不应阻塞本地训练。

## 普通 LLM API

桌面页面把常用配置收敛为：服务、Key 或本地地址、模型、测试连接、保存。Endpoint、显示名称与连接 ID 在高级设置中。

打包桌面重点验证：

- OpenAI；
- OpenAI-compatible；
- Ollama `/v1`。

源码安装的统一 Provider 层还支持 Anthropic 与 Gemini。当前语音转录只走 OpenAI / OpenAI-compatible 的 `/audio/transcriptions` 接口；它是面试回答的可选草稿工具，不会自动提交或评分。Embedding、图像生成、RAG、MCP Runtime 与 Tool Marketplace 不在本版本范围内。

### 安装

```bash
python -m pip install -e ".[ai]"
```

Python 3.11 是统一 Provider 可选依赖的推荐版本。

### 常见错误

- `401`：检查系统密钥环中的 Key；
- `429`：等待限流窗口，减少重试频率；
- `500 / 502 / 503`：服务临时错误，稍后重试；
- Timeout：检查网络、Endpoint 和本地服务；
- Ollama 未启动：启动 Ollama，再测试 `http://127.0.0.1:11434`；
- Keyring 不可用：不会回退到明文文件，继续使用 No-AI。

界面日志只记录经过清理的错误类别，不记录 Authorization Header、Key 或完整 Prompt。

### 面试语音转录（可选）

非代码面试回答可以先在本机录音，再由用户主动点击“转录到回答框”。录音默认保存在当前学习档案的面试目录；只有选择已测试的 OpenAI / OpenAI-compatible AI 服务并勾选本场远程授权后，音频才会发送。转录结果只是可编辑草稿，仍需检查、修改并点击“提交并锁定回答”。

没有麦克风、转录服务不可用、网络中断或不愿发送音频时，直接使用文字回答即可。应用不会把音频写入 Profile YAML、事件日志或普通配置，也不会因为转录失败阻塞 No-AI 训练。

## 上下文预览

远程请求默认只允许包含：

- 当前公开题面；
- 用户主动选择的当前答案；
- 最近一次公开测试摘要；
- 当前岗位与 Skill；
- 当前帮助等级；
- AI 行为规则。

默认排除：整个 Workspace、其他学习档案、旧答案、Git 历史、雇主材料、Oracle、Private Tests、API Key 和未授权材料。

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
- Coach、Reviewer、Interviewer、Repository Agent 模式。

Coach、Reviewer 与 Interviewer 默认只读，不修改答案。Repository Agent 只面向维护者和贡献者，并使用显式审批。

在桌面端“设置 → 模型与推理强度”中可以为 Codex 选择模型 ID 和 `default / low / medium / high / xhigh` 推理强度。该设置同时用于 Coach、面试评估和个性化面试计划；只影响新的 Codex 请求。面试设置页选择“Codex”后也会显示当前值并提供“修改”入口。Codex 计划只生成经过本地蓝图校验的非代码问题，用户确认前不会创建面试会话。

### macOS 查找 Codex

Finder 启动的 `.app` 不保证继承登录 Shell 的 PATH。应用依次检查：

- 用户在设置中选择的路径；
- 当前 PATH；
- `/opt/homebrew/bin/codex`；
- `/usr/local/bin/codex`；
- 常见的 `.local`、npm、Volta 与 Bun 用户目录。

设置中只保存非敏感可执行文件路径。未检测到或未登录时，No-AI 和普通 API 继续可用。

### 操作审批

涉及命令或文件改动时，GUI 显示：

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

AI 可以解释前置、给 H1 / H2 / H3 提示、分析 traceback、审查 Shape / Mask / Gradient / 数值稳定、进行口述追问和建议下一节点。

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
