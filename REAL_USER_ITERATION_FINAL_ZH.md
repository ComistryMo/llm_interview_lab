# 真实用户迭代最终报告

## 基线

- 代码集成提交：`79db3fc301128ce509384b66fc2bade4f4147e51`；最终交接时的 HEAD 以 `git rev-parse HEAD` 为准，分支为 `feature/real-user-iteration-20260831`，工作树应保持干净；基线提交 `d52238f646aee5aa7cc85ce2ba740b272aaa9c5a`。
- Python：`3.11.9`（统一使用 `py -3.11`）。
- 既有唯一一次本地全量回归：`py -3.11 -m pytest -q` → **507 passed, 14 skipped in 834.32s**。本轮没有重复运行。

## 实际根因

- 首用材料边界此前只把 PDF/DOCX 当作不透明附件，无法在获得明确授权后提供可审计的文本上下文。
- 个性化计划缺少“上下文预览 → Provider 生成 → 严格解码 → 用户确认 → 冻结”的完整链路，存在把模型输出直接当作面试事实的风险。
- 语音回答没有真实的本地录音、授权转录和可编辑草稿通道；跨题/跨 Profile 状态隔离也需要显式身份键。
- 连接状态曾可能由界面展示文案推断；这会把“已连接”文字误当作真实可用状态。
- 材料卡片在缺少可选 `text_snapshot` 字段时会提前求值，导致 QML 页面/截图出现 TypeError。

## Slice D

- 已实现 PDF 文本提取（不做 OCR）和 DOCX 段落/表格提取；原文件仍保留在当前 ignored Profile，文本快照绑定源文件 SHA-256，源文件变更后授权失效。
- 已实现受控个性化面试 Golden Path：`post_training_engineer + new_grad + medium`。计划上下文包含岗位蓝图、已审核知识主题和用户逐场授权的材料；Provider 只能返回非代码问题文字，Coding 题、Rubric、时长和题型仍由本地确定性代码决定。
- 计划在写入前必须预览并显式确认；严格检查 JSON、问题数量、round/kind、标题/提示长度和整数位置，计划与上下文 SHA 一起冻结到当前 Profile。
- 已实现真实 Qt Multimedia 本地录音：`录音 → 停止 → 选择连接并勾选授权 → OpenAI-compatible 转录 → 可编辑草稿`。转录失败不阻塞文字回答；音频不写入事件日志、普通配置或 Git。
- 连接 `ready` 是控制器布尔字段，仅在测试成功后置为真；QML 不再解析“已连接”等展示字符串。
- 切换 Profile、加载无面试 Profile 或切换问题时会清理录音、转录和待确认计划，防止状态串档。
- 修复材料卡片对缺失快照字段的安全读取，避免后端为空 fixture 触发 QML TypeError。

## Luna Max 委派

- Task：分别请求子 Agent 审查 UI/Profile/Windows 与本轮 Slice D。
- 调用标识：多次服务端返回 HTTP 429；一次替代模型因容量不足失败。
- 返回结果：没有可采纳的 Patch 或独立报告。
- Main Review：记录 `LUNA_DELEGATION_UNAVAILABLE`，由主控按同一边界完成实现和逐文件审查；未伪造子 Agent 结果，也未重复调用。

## 修改文件

- `src/llm_interview_lab/materials.py`、`workspace/schema/material.schema.json`：材料文本快照、SHA 绑定、路径与 UTF-8 校验。
- `src/llm_interview_lab/ai/context_builder.py`、`src/llm_interview_lab/ai/interview_planner.py`：最小上下文预览和 Provider 输出严格解码。
- `src/llm_interview_lab/application.py`、`src/llm_interview_lab/role_interviews.py`、`workspace/schema/role-interview-session.schema.json`：预览/确认/冻结个性化面试计划，保留旧面试 API。
- `src/llm_interview_lab/ai/transcription.py`、`src/llm_interview_lab/desktop/voice.py`、`src/llm_interview_lab/desktop/controller.py`：本地录音、显式远程授权、转录草稿和异步身份校验。
- `src/llm_interview_lab/desktop/qml/pages/CareerPage.qml`、`InterviewPage.qml`、`desktop/i18n.py`：能力提示、计划预览、语音控件与可执行错误。
- `tests/infrastructure/test_career_materials.py`、`test_role_interviews.py`、`test_transcription.py`、`test_voice.py`、`test_desktop.py`：快照、计划、严格字段、语音、Profile/异步隔离和 QML 契约。
- `pyproject.toml`：加入 `pypdf` 运行依赖；README 与 `docs/ai-connections.md`、`docs/desktop-app.md`、`docs/interviews.md` 同步真实边界。

## 目标测试

- `py -3.11 -m pytest tests/infrastructure/test_career_materials.py -q` → **25 passed, 3 skipped**。
- `py -3.11 -m pytest tests/infrastructure/test_role_interviews.py -k "personalized_plan" -q` → **5 passed, 30 deselected**。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "personalized_plan or transcription" -q` → **4 passed, 29 deselected**。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "truthful_desktop_pages_render_at_1080x680" -q` → **4 passed, 29 deselected**。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "personalized_plan or transcription or connection or truthful_desktop_pages_render_at_1080x680" -q` → **9 passed, 24 deselected in 38.03s**。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "connection or demo_controller_never_persists" -q` → **1 passed, 32 deselected**。
- `py -3.11 -m pytest tests/infrastructure/test_transcription.py tests/infrastructure/test_voice.py tests/infrastructure/test_role_interviews.py -q` → **40 passed**（在最后一轮小修复前完成；后续改动由上面的受影响用例覆盖）。
- 相关模块 `py_compile` 和 `git diff --check` → 通过（QML 仅有换行格式提示，无空白错误）。

## 全量与 CI 预算

- 本地全量严格只执行一次：`507 passed, 14 skipped`。
- 本轮没有触发新的 RC CI，也没有重复整个 CI 矩阵；计划中的 RC 门禁仍未满足。

## 实机验收

- 本轮未取得 Windows standalone Explorer 双击、中文/空格路径、损坏资源错误框的实机证据。
- 本轮未取得 macOS 打包产物、真实麦克风、Keychain 或远程付费 Provider 的平台验收证据。
- 已验证源码测试环境中的 No-AI、Profile 隔离、QML 页面加载和异步结果身份检查。

## Artifact

- 本轮没有生成或发布新的 Windows/macOS 安装包，因此不提供虚构的大小或 SHA-256。
- 测试与源码变更未包含真实 Profile、材料正文、答案、Key、Oracle 或 Private Tests。

## Git / 远端

- 已提交两个逻辑提交：`7f0667d feat(interview): add consent-bound personalized plans and snapshots`、`7ef4c3a feat(interview): add profile-local voice answer flow`。
- 分支：`feature/real-user-iteration-20260831` 已推送至 `origin`，远端 SHA 为 `79db3fc301128ce509384b66fc2bade4f4147e51`；PR 创建链接：<https://github.com/ComistryMo/llm_interview_lab/pull/new/feature/real-user-iteration-20260831>。当前环境 `gh` 未登录，因此未代创建 PR；未合并 `main`、未重写历史、未创建 tag 或 Release。

## 剩余风险

- `LUNA_DELEGATION_UNAVAILABLE`：没有外部独立子 Agent 结果。
- `BLOCKED_BY_MISSING_WINDOWS_RUNTIME`：缺少 Windows standalone Explorer 双击和失败弹框验收。
- `BLOCKED_BY_MISSING_MACOS_RUNTIME`：缺少 macOS 构建/运行和真实 Keychain 验收。
- 语音 MVP 已有源码级真实录音与可编辑转录路径，但尚未证明所有操作系统的麦克风权限、编解码器和远程服务兼容性。
- 当前仅开放一个个性化 AI 面试配置；其他岗位和蓝图仍使用确定性固定流程。

## 最终裁决

**PARTIAL**：Slice D 的源码闭环和定向验证已完成；由于 RC CI、Windows/macOS 产物和实机验收尚未完成，本分支不满足合并 `main`、打 tag 或发布 Release 的条件。
