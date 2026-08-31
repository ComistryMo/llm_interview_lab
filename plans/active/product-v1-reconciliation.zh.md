# Product V1 现状对齐审计

> 审计基线：`feature/product-v1-phase0@fa0c10afb605ccbbd7143f8bac977392dccb03d8`。本报告只描述当前源码事实与最小迁移建议，不把历史测试结果当作本轮最终验收。

## 读取范围与判断方法

已读取产品总 Plan、`REAL_USER_ITERATION_FINAL_ZH.md`、`AGENTS.md`、`PLANS.md`、`docs/architecture.md`，并核对当前分支相对 `origin/main` 的真实差异（63 个已跟踪文件，主要是 Slice D 材料、个性化计划、语音和桌面体验）。每项只使用一个裁决：`KEEP`、`KEEP_WITH_SMALL_FIX`、`ADAPT`、`REPLACE`、`REMOVE` 或 `NOT_STARTED`。

## 逐项对齐

### 1. PDF/DOCX 提取与源文件/文本快照 SHA — `KEEP_WITH_SMALL_FIX`

- **Plan 要求：** 本地提取 PDF/DOCX，保存原文件 SHA 与提取文本 SHA，并在源文件变化时使旧授权失效。
- **当前实现：** `materials.py::_extract_pdf_text` 使用 `pypdf`，`_extract_docx_text` 解析段落/表格；`add_material` 写入原文件、文本快照及 `text_snapshot_source_sha256`；`resolve_material_text_path` 校验源文件仍匹配。
- **精确证据：** `src/llm_interview_lab/materials.py`：`MaterialRecord`、`_extract_pdf_text`、`_extract_docx_text`、`add_material`、`resolve_material_text_path`；`workspace/schema/material.schema.json`。
- **可复用资产：** 原子写入、路径安全、UTF-8 规范化和现有材料测试。
- **冲突/风险：** PDF 扫描件没有 OCR，提取质量和页级定位尚未产品化。
- **最小迁移：** 增加预览/质量标记和失败提示，不改快照事实模型。
- **Plan Phase：** Phase 2（材料可靠性）。

### 2. 材料逐场授权、Context Preview、原文件与提取文本独立授权 — `ADAPT`

- **Plan 要求：** 原始文件发送与提取文本发送分开授权；每场显示材料 ID、用途和 SHA，并在发送前预览。
- **当前实现：** `ApplicationService.personalized_interview_context` 生成受限上下文；`_material_references` 要求 `consent_materials=True` 并记录材料 SHA；Controller/QML 有上下文预览。但当前授权粒度只有材料级 `ai_access`/本场 consent，未拆成 raw/text 两项。
- **精确证据：** `src/llm_interview_lab/application.py::personalized_interview_context`、`src/llm_interview_lab/role_interviews.py::_material_references`、`src/llm_interview_lab/desktop/controller.py::personalizedInterviewPlanContext` 与 QML `personalizedInterviewContextDialog`。
- **可复用资产：** `MaterialRecord`、上下文 SHA、Context Preview 对话框。
- **冲突/风险：** 目前不会把原始 PDF/DOCX 内容直接发送，但模型和界面仍把 consent 语义表达成单一开关。
- **最小迁移：** 将 consent snapshot 扩展为 `text`/`raw_file` 两个布尔值，默认 raw 为 false；旧记录按 text consent 兼容读取。
- **Plan Phase：** Phase 2/5。

### 3. “使用上一次材料组合” — `NOT_STARTED`

- **Plan 要求：** 记住上次组合并预选，但每场仍需再次确认，不自动发送。
- **当前实现：** Session 保存 `material_refs`，但没有可供下一场复用的组合选择或确认 UI。
- **精确证据：** `role_interviews.py::_create_session_from_plan`、`application.py::create_personalized_interview`；未发现 previous-material 解析入口。
- **可复用资产：** `material_refs` 的 ID/SHA 快照。
- **冲突/风险：** 直接复用旧 SHA 会在材料变更后误授权。
- **最小迁移：** 只保存最近组合的 ID/SHA，加载时逐项重新校验并要求确认。
- **Plan Phase：** Phase 2。

### 4. Profile 恢复和跨 Profile 隔离 — `KEEP_WITH_SMALL_FIX`

- **Plan 要求：** 重启可恢复，异步任务、录音、转录和报告不得跨 Profile 串联。
- **当前实现：** `workspace.profile_paths`/`load_profile` 以显式 Profile 为根；Controller 保存 active Profile，异步 completion 检查 Profile/operation 身份；语音状态在切换时清理。
- **精确证据：** `src/llm_interview_lab/workspace.py::profile_paths`、`src/llm_interview_lab/desktop/controller.py::_restore_active_profile_id`、`_load_profile_state`、`_load_interview`、`transcribeInterviewRecording`。
- **可复用资产：** ignored Profile、路径守卫、operation identity checks。
- **冲突/风险：** 仍需要覆盖更多重启恢复场景和旧数据迁移提示。
- **最小迁移：** 保持 Domain 不变，补恢复视图和针对性重启测试。
- **Plan Phase：** Phase 2/7。

### 5. Connection `ready` 结构化状态 — `KEEP`

- **Plan 要求：** UI 只读取真实结构化连接能力，不能从显示文案猜测“已连接”。
- **当前实现：** `ProviderConfig`/Controller 的连接项含布尔 `ready`，仅测试成功后置真；QML `providerIsReady` 直接判断 `item.ready === true`。
- **精确证据：** `src/llm_interview_lab/desktop/controller.py::connections`、`testConnection`、`InterviewPage.qml::providerIsReady`；`tests/infrastructure/test_ai_connections.py`。
- **可复用资产：** Keyring 引用、mock provider、连接测试流程。
- **冲突/风险：** `ready` 仍是粗粒度状态，未来需补能力字段但不应破坏现有布尔字段。
- **最小迁移：** 增量加入 capability flags，保留 `ready` 兼容。
- **Plan Phase：** Phase 2。

### 6. 当前预生成整场非代码问题的 Planner — `REPLACE`

- **Plan 要求：** 面试前只冻结设置、材料、Coverage Contract；每轮动态生成当前问题。
- **当前实现：** `decode_personalized_questions` 要求 Provider 一次返回覆盖蓝图全部非代码位置的 `questions` 数组；Controller `generatePersonalizedInterviewPlan` 收集完整响应，`confirmPersonalizedInterviewPlan` 再写入 session。
- **精确证据：** `src/llm_interview_lab/ai/interview_planner.py::decode_personalized_questions`（`len(raw_questions) != len(expected)`）；`src/llm_interview_lab/desktop/controller.py::generatePersonalizedInterviewPlan`、`confirmPersonalizedInterviewPlan`；`role_interviews.py::_build_questions`。
- **可复用资产：** 严格 JSON 解码、上下文 SHA、Coding 题本地确定性选择和一次重试边界。
- **冲突/风险：** 继续扩展会泄露未来问题，并无法让后续问题真正依赖前序回答；历史 `507 passed` 不能证明目标语义正确。
- **最小迁移：** 新增运行时 `NextTurn` 协议；旧 Planner 仅作为训练模式/兼容迁移路径，不在严格模拟中调用。
- **Plan Phase：** Phase 6。

### 7. 当前 Blueprint、冻结问题列表和 Session Schema — `ADAPT`

- **Plan 要求：** Blueprint 退为隐藏 Coverage Contract，Session v2 只保存已实际提出的 Turn。
- **当前实现：** `role_interviews.py::_build_questions` 按 Blueprint 构造完整 `questions`；`_create_session_from_plan` 写入 schema v1 的完整列表，另有 `blueprint_coverage` fallback 字段。
- **精确证据：** `src/llm_interview_lab/role_interviews.py::_build_questions`、`_create_session_from_plan`、`load_role_interview`；`workspace/schema/role-interview-session.schema.json` 的 `questions`/`blueprint_coverage`；`roles.py::RoleCatalog`。
- **可复用资产：** 轮次权重、Coding 题指纹校验、assessment/followup 记录。
- **冲突/风险：** 直接改 schema 会影响旧 session 和 CLI 报告。
- **最小迁移：** 保留 schema v1 读取；新增 v2 writer/adapter，仅把未来题目移入 contract，历史 session 只读。
- **Plan Phase：** Phase 6。

### 8. 最终动态一问一答面试状态机 — `REPLACE`

- **Plan 要求：** `GENERATING_CURRENT_QUESTION → ASKING → ANSWER_SUBMITTED → ANALYZING → GENERATING_NEXT`，支持暂停/恢复。
- **当前实现：** 当前状态机沿 `session["questions"]` 顺序由 `_next_role_question` 选择第一个未完成题；`current_role_question` 返回已冻结题。
- **精确证据：** `src/llm_interview_lab/role_interviews.py::_next_role_question`、`role_interview_state`、`current_role_question`、`record_role_answer`；`application.py::current_interview`/`answer_interview`。
- **可复用资产：** 现有 pause/resume、deadline、assessment 和 timeline 机制。
- **冲突/风险：** 不能通过界面措辞补救预生成语义。
- **最小迁移：** 以同一 session identity 增加 turn append-only 存储，先实现非代码动态路径，再迁移 UI。
- **Plan Phase：** Phase 6。

### 9. 用户背景、授权材料、前序对话和当前回答的上下文连续性 — `REPLACE`

- **Plan 要求：** 每个下一问读取已授权背景、全部前序对话、当前回答、已覆盖能力和剩余时间。
- **当前实现：** `personalized_interview_context` 只在生成整场计划时提供一次受限背景；后续 `record_role_answer`/`record_role_followup` 不调用动态 Provider 生成下一问。
- **精确证据：** `application.py::personalized_interview_context`、`create_personalized_interview`；`role_interviews.py::record_role_answer`、`record_role_followup`。
- **可复用资产：** context builder 的 bounded role-scoped themes、材料引用和答案 SHA。
- **冲突/风险：** 将整份 Profile 或原始材料塞入每轮会违反最小上下文和隐私边界。
- **最小迁移：** 构造每轮有上限的 context summary，只传明确授权材料和当前/历史证据。
- **Plan Phase：** Phase 6/7。

### 10. Coding 题由本地验证题库决定 — `KEEP`

- **Plan 要求：** Coding 题只能来自 ready、验证有效的本地 Catalog；AI 不决定测试或 mastery。
- **当前实现：** `_coding_candidates` 从 Catalog 筛选，`start_role_interview` 重新计算问题 fingerprint；Grader 和 Practice 由本地确定性代码裁决。
- **精确证据：** `role_interviews.py::_coding_candidates`、`start_role_interview`；`catalog.py::Problem.recommendable`、`_validate_fingerprints`；`grader.py`。
- **可复用资产：** Catalog/DAG、fingerprint、grader 状态和 SHA 证据。
- **冲突/风险：** 统一工作台尚未把 Practice 与 Interview 的 Coding UI 合并。
- **最小迁移：** 先复用现有 grader/use case，新增工作台只做呈现层。
- **Plan Phase：** Phase 3/4。

### 11. Qt 本地录音 — `KEEP_WITH_SMALL_FIX`

- **Plan 要求：** 本地录音、权限/设备异常可恢复，音频默认不上传。
- **当前实现：** `InterviewVoiceRecorder` 用 Qt Multimedia 写 WAV，状态为 idle/recording/recorded/error；Controller 将录音路径限制在当前 Profile。
- **精确证据：** `src/llm_interview_lab/desktop/voice.py::InterviewVoiceRecorder`；`controller.py::startInterviewRecording`/`stopInterviewRecording`；`tests/infrastructure/test_voice.py`。
- **可复用资产：** WAV recorder、状态信号、Profile path guard。
- **冲突/风险：** 未完成 Windows/macOS 真实麦克风权限和编解码器验收。
- **最小迁移：** 增加设备权限提示和统一暂停状态，保持轮次式录音。
- **Plan Phase：** Phase 8。

### 12. OpenAI-compatible 远程 STT — `ADAPT`

- **Plan 要求：** 远程 STT 只能是用户主动配置、独立授权的高级选项。
- **当前实现：** `OpenAICompatibleTranscriber.transcribe` 调用 `/audio/transcriptions`，强制 `consent_remote=True`，Controller 将结果放入可编辑草稿。
- **精确证据：** `src/llm_interview_lab/ai/transcription.py::OpenAICompatibleTranscriber`；`controller.py::transcribeInterviewRecording`；`docs/ai-connections.md`。
- **可复用资产：** API timeout、错误脱敏、显式 consent、可编辑草稿路径。
- **冲突/风险：** 当前没有本地模型默认路径，不能宣称已满足本地优先 STT。
- **最小迁移：** 将远程适配器包装成显式 Advanced Remote STT；加入本地实现选择和状态显示。
- **Plan Phase：** Phase 8。

### 13. 本地 STT 默认路径 — `NOT_STARTED`

- **Plan 要求：** 默认离线本地模型，网络不可用时仍可转录。
- **当前实现：** 仓库无本地 STT 模型、加载器或推理入口；唯一转录类是远程 `OpenAICompatibleTranscriber`。
- **精确证据：** `src/llm_interview_lab/ai/transcription.py` 全文件；`pyproject.toml` 无本地 STT 依赖；`desktop/voice.py` 只负责录音。
- **可复用资产：** 录音 WAV 和 transcript state。
- **冲突/风险：** 模型体积、许可证、CPU 性能和首次下载 UX 尚未决策。
- **最小迁移：** 先做本地 provider contract 和按需模型包 Spike，再决定模型，不在本 Phase 引入。
- **Plan Phase：** Phase 8A。

### 14. 本地-only TTS — `NOT_STARTED`

- **Plan 要求：** 朗读始终本地，可选男/女声、试听和失败降级。
- **当前实现：** 没有 TTS service、声音选择或 QML 播放入口。
- **精确证据：** `rg` 未发现 `tts`/`QTextToSpeech`/本地语音实现；`InterviewPage.qml` 仅有录音/转录控件。
- **可复用资产：** 面试问题文本、语音状态卡。
- **冲突/风险：** Qt/系统语音能力在 Windows/macOS/Linux 不一致。
- **最小迁移：** 先定义文字降级和本地系统 voice adapter；不接远程付费 TTS。
- **Plan Phase：** Phase 8C。

### 15. 训练模式可编辑 Transcript 与严格模拟原始 Transcript — `ADAPT`

- **Plan 要求：** 训练转录可编辑；严格模拟保留不可覆盖原始文本，复盘副本不改变评分依据。
- **当前实现：** 远程转录结果进入 editable draft，Controller 有 transcript state；但 session schema 没有 raw transcript 与 review copy 的双轨字段，且没有 strict/guided 语义分离。
- **精确证据：** `controller.py::transcribeInterviewRecording`、`InterviewPage.qml::interviewVoiceCard`；`role-interview-session.schema.json` 未定义 transcript provenance 字段。
- **可复用资产：** profile-local answer files、answer SHA、`answer_locked`/corruption 校验。
- **冲突/风险：** 将可编辑草稿直接当严格证据会破坏报告可信度。
- **最小迁移：** 增加 mode-aware transcript record；严格模式写 immutable raw，再生成副本。
- **Plan Phase：** Phase 7/8。

### 16. 统一编程工作台 — `NOT_STARTED`

- **Plan 要求：** Practice 与 Interview 共用题面/编辑器/Case/Grader 结果工作台。
- **当前实现：** `ExercisePage.qml` 和 `InterviewPage.qml` 各自有编辑器/测试相关 UI；没有统一 Workbench 组件或统一 Case 模型。
- **精确证据：** `src/llm_interview_lab/desktop/qml/pages/ExercisePage.qml`、`InterviewPage.qml`；`application.py::run_practice_tests_for_submission` 与 `test_interview_coding` 是分离入口。
- **可复用资产：** 当前提交保存、Grader SHA、Coding evidence 和题面字段。
- **冲突/风险：** 直接合并页面会复制状态和混淆 Practice/Interview 证据边界。
- **最小迁移：** 先抽一个仅呈现层 Workbench，业务动作继续调用现有 use case。
- **Plan Phase：** Phase 3/4。

### 17. 官方答案与 Assisted/Mastery 规则 — `NOT_STARTED`

- **Plan 要求：** 公开经过验证的官方答案；查看后标记 Assisted，并要求新无帮助变式才能独立掌握；严格面试排除已看答案原题。
- **当前实现：** Catalog/Grader 支持题面和测试，但公共题目默认四文件契约，无 `official_solution.py`/解锁事件；未发现 Assisted 状态规则。
- **精确证据：** `catalog.py::PROBLEM_ASSETS`、`_validate_assets`；`workspace/schema/event.schema.json` 与 `events.py` 未定义 official-view mastery 语义。
- **可复用资产：** retention assets、submission SHA、mastery reducer。
- **冲突/风险：** 直接把答案放入现有题目目录会改变公共资产契约，且可能泄露维护者答案。
- **最小迁移：** 先设计独立公开 solution asset 与事件，不在本 Phase 添加参考答案。
- **Plan Phase：** Phase 4。

### 18. 三套视觉方向与新设计系统 — `ADAPT`

- **Plan 要求：** 在批量重写 UI 前，以同一 Coding Workbench 内容制作 Graphite Blue、Obsidian Violet、Warm Frost 的深浅原型并选定方向。
- **当前实现：** 已有 Quiet Forge `AppTheme.qml`、共用卡片/按钮组件和桌面截图脚本；Phase 0 已保留三方向六张合成原型，当前正式决策为 `VISUAL_DIRECTION_SELECTED_GRAPHITE_BLUE`。
- **精确证据：** `src/llm_interview_lab/desktop/qml/components/AppTheme.qml`、`LabCard.qml`、`LabButton.qml`；`scripts/capture_desktop_screenshots.py`。
- **可复用资产：** QML offscreen screenshot harness、主题 token、现有字体选择。
- **冲突/风险：** 原型是静态合成证据，不能冒充正式工作台；一次性替换全部 QML 会扩大跨平台风险。
- **最小迁移：** Phase 2 只将 Graphite Blue 的冷中性表面、细分隔线、单一 CTA，以及 Warm Frost 的浅色长文本暖灰微差吸收到首用入口/设置/首题路径；Obsidian Violet 仅保留低饱和选中和 AI 辅助细节。
- **Plan Phase：** Phase 1（方向冻结）→ Phase 2（局部正式页面适配）。

### 19. 证据化报告、导出和删除 — `ADAPT`

- **Plan 要求：** 报告引用原回答/材料/Grader 证据，支持 Markdown/JSON/录音/代码导出和细粒度删除。
- **当前实现：** `role_interviews._write_role_report` 生成 profile-local `report.md`/`report.json`，记录 assessment source/evidence、followup 和 coding SHA；Workspace 预留 `exports/`，但没有面试证据跳转、导出编排或细粒度删除 API。
- **精确证据：** `src/llm_interview_lab/role_interviews.py::_write_role_report`、`role_interview_report`；`workspace.py::profile_paths`；`docs/workspace.md`。
- **可复用资产：** report JSON、timeline、answer/coding 文件和路径守卫。
- **冲突/风险：** 导出可能意外包含材料正文或绝对路径，删除必须可恢复且不误删 Profile。
- **最小迁移：** 先增加显式、脱敏的 export manifest，再做逐项确认删除；不把报告写进公共树。
- **Plan Phase：** Phase 7/9。

### 20. Windows/macOS/RC/Release 门禁 — `ADAPT`

- **Plan 要求：** Windows/macOS 真实平台验收、Artifact 隐私、一次最终全量和一次 RC CI 后才发布。
- **当前实现：** `.github/workflows/ci.yml` 已有 Windows standalone、macOS arm64、CPU/文档 Job；`scripts/build_macos_desktop.py`、`check_*_artifact.py` 和现有截图/隐私契约存在。历史报告明确尚缺真实 Windows Explorer 双击、macOS 包/Keychain/麦克风实机和新的 RC CI。
- **精确证据：** `.github/workflows/ci.yml::desktop-windows`、`desktop-macos-arm64`；`scripts/build_macos_desktop.py`、`scripts/check_macos_artifact.py`、`scripts/check_desktop_artifact.py`；`REAL_USER_ITERATION_FINAL_ZH.md`“实机验收/Artifact”。
- **可复用资产：** 固定 runner、artifact privacy checks、release workflow。
- **冲突/风险：** 不能把 CI offscreen 或历史 `507 passed` 当作本轮发布证据，也不能在本 Phase 触发打包。
- **最小迁移：** 先保留现有门禁，后续只补缺失的动态面试/语音与真实平台证据。
- **Plan Phase：** Phase 10。

## 强制语义结论

1. **当前 `interview_planner.py` 确实一次返回并冻结全部未来非代码问题。** `decode_personalized_questions` 按 Blueprint 计算完整 expected positions，并拒绝数量不等的响应；Controller 收集完整流后才进入 preview/confirm，`create_role_interview` 把完整 `questions` 写入 session。因此它不能被描述为动态面试。
2. **三种状态必须分开：** 未来尚未生成的问题应只存在于隐藏 Coverage Contract；当前实际展示并冻结的问题是 Current Turn；已完成的问题才进入 session 的 completed turn/evidence。现有 `questions` 列表把后两者与未来问题混在一起，是 Phase 6 的替换边界。
3. **现有转录只能称为可选远程 STT 适配器。** `OpenAICompatibleTranscriber` 需要用户连接和 `consent_remote`，仓库没有本地 STT 默认实现；不能把它宣传为本地默认 STT。
4. **测试全绿不等于产品语义已对齐。** 历史测试证明当前实现的旧契约，但对预生成计划、可编辑严格 Transcript、本地 STT 缺失等冲突不构成合入 `main` 的理由；后续必须按 Plan 的新语义补测试和迁移。

## 最短后续实施序列（最多三片）

1. **PR-1：视觉方向与基础入口。** 用户从六张原型中选定方向；再吸收 Workbench token，统一 Practice/Interview Coding 入口，并补 Profile/材料 consent 的最小 UI。
2. **PR-2：动态文字面试。** 新增 Coverage Contract + append-only Turn/session v2，保留旧 session 读取适配；实现 guided/strict 双模式、逐轮上下文和证据状态机。
3. **PR-3：语音与证据报告。** 本地 STT 默认、远程可选、本地 TTS、raw/review transcript 双轨和脱敏导出/删除，再做 Windows/macOS 真实验收与 RC 门禁。
