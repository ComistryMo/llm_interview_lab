# ExecPlan：Codex/Claude 风格本地训练工作台打磨

## 目标与可观察结果

在现有 PySide6/Qt Quick 与 Application/Core 之上，交付可恢复、local-first 的桌面训练工作台：陌生用户能从 Onboarding 进入第一题；Practice 以编辑器为焦点且在 900×620/1080×680 不裁切；Coach 支持多个本地可恢复会话、发送/停止/重试/复制和显式上下文；Interview 清楚区分回答与评估阶段；Connections 的 No-AI/offline 路径始终可用。Light/Dark、系统主题、键盘焦点和所有按钮状态均有真实行为。AI 不修改答案、不授予 mastery，旧页面/旧异步结果不能覆盖当前会话。

验收证据包括定向测试、真实应用合成截图及 manifest；截图不得包含真实 Profile、材料、答案、Transcript、Oracle、Private Tests 或 Secret。

## 当前仓库事实

- Alpha3 基线分支 `fix/v0.4.0-alpha.3-truthful-ux` 在本轮合并前为 `85d4786`（开始整合时工作树干净）；面经内容分支以非强制合并提交 `30798ab` 纳入，未重写双方历史。
- 桌面入口：`src/llm_interview_lab/desktop/main.py`、`desktop/controller.py`、`desktop/qml/Main.qml` 与 `qml/pages/*.qml`。
- Controller 已有 Provider/Codex 流式调用、审批、Practice/Interview 上下文预览，但 Coach 消息只通过短生命周期信号传递，没有 profile-scoped session store。
- 业务事实仍由现有 ApplicationService、Practice/Interview API、Catalog 和 Profile events 决定；不建立第二套业务状态。
- 既有未跟踪文件 `.tmp_controller_extract.txt` 与 `llm_interview_lab_runtime_blockers_agile_review_zh.md` 不读取、不修改、不删除。

## 范围与明确不做

范围：桌面 QML 层级与响应式布局、桌面 Controller 的薄 Coach session 接口/异步身份校验、必要的 schema/忽略规则、Interview 阶段文案与真实状态、截图与定向测试。

明确不做：新增课程/题目/Provider 类型；修改真实 Profile、Submission、材料、Events、Oracle、Private Tests 或 API Key；自动改答案或写 `task_mastered`；数据库、服务端、插件/遥测、多 Agent runtime；Electron/Tauri/WebView；大型 Design System；读取其它 Profile 或整个 Workspace；覆盖用户数据的 git 命令。

## 分阶段里程碑

1. **地图与评审（已完成）**：只读当前 QML、Controller、AI/Interview 流程和现有合成截图；收集具体 P0/P1 发现，锁定写入者。
2. **高价值桌面 UI**：由唯一 QML 实施者改 Shell、Home/Learn/Exercise/Interview/Coach/Connections/Settings；保持 backend API 兼容，补空/错误/disabled/focus 状态和窄窗口布局。
3. **Coach 本地会话**：在当前 Profile 下新增 `coach/sessions.json`（必要时 schema），Controller 提供 `coachSessions`、`activeCoachSession`、`coachMessages`、`coachStreaming`、`coachError` 与 create/select/delete/send/stop/retry；上下文只用现有 preview builder，异步结果带 profile/session/operation/message/provider 身份并丢弃过期结果。
4. **Interview/连接整合**：不改变核心评分事实源；明确回答锁定、评估证据来源、暂停/恢复/结束和 No-AI/offline 提示；Codex 探测不阻塞启动，审批/文件 Diff 仍显式。
5. **验证与截图（已完成）**：先跑受影响的定向测试（session persistence、provider stream/stop/retry/error、interview phase、profile isolation、context privacy、screenshot contract），使用 demo/synthetic 数据生成八页 × 四尺寸 × Light/Dark 截图和 manifest；最后只在用户授权后运行一次 `python -m pytest -q`。
6. **独立 Review 与收尾（已完成）**：实现者之外的 Review Agent 检查代码/视觉/产品，只修 P0 与明确影响用户的 P1；将本计划移动到 `plans/completed/codex-claude-ui-polish.md`，确认分支、commit、工作树。

## 每阶段测试命令

- QML/桌面静态与现有契约：`python3 -m pytest -q tests/infrastructure/test_desktop.py tests/infrastructure/test_alpha3_truthful_ux.py tests/infrastructure/test_onboarding_qml_hotfix.py`
- Coach/Provider/隐私：`python3 -m pytest -q tests/infrastructure/test_ai_connections.py tests/infrastructure/test_ai_context.py` 加新增的 session 定向测试。
- Interview：`python3 -m pytest -q tests/infrastructure/test_mock_interviews.py tests/infrastructure/test_mock_interview_security.py tests/infrastructure/test_mock_interview_cli.py`
- 截图：`python3 scripts/capture_desktop_screenshots.py --help` 后仅使用 demo/synthetic 入口运行实际尺寸契约。
- 最终（仅用户授权）：`python -m pytest -q`。

## 风险、回退和停止条件

- PySide6/平台运行时可能不可用：保留静态契约测试和 demo 截图证据，明确标记未验证平台；不伪称通过。
- Provider 流可能晚到或重复：所有回调校验 profile/session/operation/message/provider；无法证明隔离时停止发布 Coach 功能。
- 会话文件损坏或旧版本字段缺失：安全降级为空会话并给出可操作错误，不触碰其它 Profile；schema 迁移只做向后兼容。
- 窄窗口裁切、中文溢出、对比度不达标或假按钮均为发布阻断；P2 只记录 backlog，不无限打磨。
- 回退优先使用小范围反向补丁或保留旧 API；禁止 `git reset --hard`、`git checkout --`、`git clean -fd`。

## 决策日志

- 2026-08-30：采用单一计划文件；QML、流程评审、Coach/Interview 评审职责分离，核心 Controller 由主维护者整合。
- 2026-08-30：会话存储固定在当前 Profile `workspace/profiles/<id>/coach/sessions.json`，不新增数据库；API Key 继续由系统密钥环管理。
- 2026-08-30：No-AI 是默认可达路径；Coach/Reviewer 默认只读，不写 Submission，不影响 mastery。

## 当前进度

- [x] 基线命令与共享仓库地图检查。
- [x] 视觉/UX/Coach 评审与 QML 改动。
- [x] Coach session 薄接口及定向测试。
- [x] Interview/Connections 整合；截图矩阵已生成并完成哈希/尺寸校验。
- [x] 独立 Review、截图归档与最终回归（全量测试仍待用户授权）。
- [x] 研究型面经/八股/手撕题知识层已合并：角色筛选、来源登记、深度研究附录和 3 个 contract-level 可运行资产均纳入同一分支。

## 最终复盘

完成时记录实际修改范围、Before/After 视觉证据、UX 流程、Coach 状态机、Interview 改进、定向测试、截图路径/manifest、独立 Review 结论、未完成事项、分支/commit/工作树；未验证内容明确标记，不以推测替代证据。

## 收口证据（2026-08-30）

- 定向测试：`test_role_interviews.py` 24 passed；Coach/desktop/onboarding 36 passed，最终 `test_desktop.py` 24 passed；AI connections/context/public workflows 53 passed；Mock Interview CLI/security/interview 82 passed；暂停/上下文/Coach/桌面组合 61 passed；`test_alpha3_truthful_ux.py` 13 passed；Codex terminal metadata 补测 4 passed。使用项目 Python 3.12 虚拟环境；系统 Python 2.7/3.9 与 PySide6 不可用，因此没有声称系统环境可运行 Qt。
- 静态检查：`python -m compileall -q src/llm_interview_lab`、`git diff --check` 通过。按用户要求未运行未经授权的全量 `python -m pytest -q`。
- 截图：`docs/images/screenshot-manifest.json` 的 `source_commit` 为代码提交 `ea4502c362af189ce8b53020f320437295bf9b3b`，`all_screenshots` 为 8 页 × 4 尺寸 × 2 主题的 64 个唯一单元；9 个旧链接保留在 `screenshots`，所有哈希均已校验，`synthetic=true`、`language=zh-CN`。
- 独立 Review：Review Agent 复核了核心边界、QML 响应式布局、Coach/Interview 状态和截图矩阵；P0/P1 已收口。剩余为 P2：Qt `palette` 属性覆盖/`Sans Serif` 字体别名警告、未在 Windows/macOS 原生窗口重拍、Interview setup 尚未增加更多候选筛选维度；不阻断当前 No-AI/本地流程。

## 交接更新：面经内容合并（2026-08-30）

### GitHub 与历史

- 仓库：`ComistryMo/llm_interview_lab`。
- 分支：`fix/v0.4.0-alpha.3-truthful-ux`。
- 合并提交：`30798ab9da2dae081a4af2c2e1b1db16e20e8071`，父提交为 Alpha3 `85d4786f8e83d9b33ac6810899af1e4705046053` 与内容分支 `31887b2`；待 GitHub 连接可用后只使用普通 fast-forward push，不使用 force push。
- 当前远端状态：仍为 `85d4786f8e83d9b33ac6810899af1e4705046053`；本地合并和报告提交尚未推送（HTTPS/SSH 均缺少可用认证）。连接 GitHub 后需重新 fetch 并用 `git ls-remote` 对账。
- 本地 `main` 已从 `origin/main=5e83f8fe3887fd8667bab347931da91fd8bc02a5` fast-forward 到 `8f36dac7adb3c236608a857c460690363f39cfd1`，包含上述 Alpha3 与知识层全部提交；由于认证阻断，`origin/main` 尚未更新。
- 推送目标现为 `main`（不是继续推送 Alpha3 分支）；连接 GitHub 后应在干净工作树执行 `git push origin main`，再核对 `git ls-remote origin refs/heads/main`。
- 本地回退锚点保留为 `backup/pre-merge-alpha3-20260830` 与 `backup/pre-merge-interview-content-20260830`；未创建 PR，真实 Profile/材料/答案未纳入提交。

### 新增交付范围

- 新增只读知识层：63 张卡片、65 条精选来源、191 条 URL-unique 来源登记，覆盖 VLM/多模态、后训练/RL、Agent/RAG、训练/推理系统和评测安全；每张卡保留 clean-room 改写、来源 claim、检索日期/版本和角色/技能筛选信息。
- 新增 `knowledge list/search/show/validate` 与 `doctor --knowledge`，桌面 Learn 页提供显式“面试知识库”入口；知识浏览不会写入 Practice、Profile events 或 mastery。
- 新增 3 个 contract-level 手撕资产：`VLM-007` 多模态 label mask、`PT-016` invalid completion handling、`INF-003` continuous batching scheduler；题面、starter、公开测试、hints 均不含参考答案，Catalog 统计变为 45 Ready / 184 Planned / 33 Oracle / 24 Retention-ready。
- 新增研究附录：`docs/research/vlm_interview_deep_dive.md`、`post_training_deep_dive.md`、`agent_inference_deep_dive.md`，并更新 `references/interview-sources.json` 与内容刷新规则。

### 合并后验证

- `doctor --knowledge`：通过（63 cards / 65 sources；Catalog 45 Ready / 184 Planned；DAG valid）。
- `knowledge validate --with-catalog --format json`：通过（schema v1、curriculum_checked=true、clean-room policy valid）。
- 受影响测试：Application/Knowledge **17 passed**；AI connections/context **24 passed**；Mock Interview CLI/security/interview **82 passed**；Role Interview **25 passed**；Catalog/Repository **76 passed**。
- 静态检查：`compileall`、JSON 解析和 `git diff --check` 通过；INF-003 独立公开测试 22/22 通过，PyTorch 相关题按环境约定跳过。
- 桌面动态测试未在本容器声称通过：PySide6 未安装，`test_desktop.py` 及 Coach/Onboarding Qt 测试按项目约定跳过，Alpha3 controller 测试无法收集；不改变原生 Windows/macOS 尚未重拍的 P2 说明。
- 未运行未经额外授权的全量 `python -m pytest -q`；后续发布前仍建议在具备 PySide6 的原生 Windows/macOS 环境执行一次最终回归和截图复核。
