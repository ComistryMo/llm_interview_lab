# Luna Max 动态面试当前状态报告

## 2026-09-05 补充：正常启动入口与真实 Codex 交互

**这是最新结果。** 下节“版本核对与输入 / 追问修复”记录的是此前 Fake 验证；本节增加实际 App Server 传输证据，不把它扩大成完整动态面试或 Release 验收。

### 基线与本轮范围

- 分支：`fix/desktop-input-interview-20260905`；起点 `d486a7540cb9086465d3506c3d09788878df3a16`。
- 再次用 `git ls-remote` 核对，GitHub `main` 仍为 `01f6b99836730d06fbf6b6a76c81b7942578db90`；公开包仍是 Alpha.3，没有被这些源码提交更新。
- 两个源码提交：`1dbcf81`（隔离源码启动资产）与 `4408f62`（真实 Codex 故障、界面与针对性测试）。不合并 main、不创建 Tag、不构建应用、不触发 CI。
- 使用正常 `desktop.main.main()`、`QApplication` 和正式 QML，通过 Qt QTest 向 Windows 窗口发送鼠标、滚轮和输入事件。这是**真实窗口自动交互**，不是维护者手工逐项验收，也不是 demo / screenshot controller。
- 所有问答均明确标为合成教学经历；没有导入、读取或发送用户简历、材料和已有 UAT 面试。应用及 Codex 的合成测试数据留在 ignored 维护者目录；没有更改全局 Codex 账号、模型设置或 CLI 安装。

### 实际发现和修复

1. **正常源码隔离启动直接失败**：仅设置 `LLM_LAB_DESKTOP_DATA_ROOT` 时，`runtime._bundle_root()` 原先只寻找编译包资源，正常 Python 安装旁没有 `curriculum`，因而退出。之前测试额外指定了 Bundle Root，掩盖了问题。源码模式现在从当前模块所在 checkout 取得公共资源；打包与显式 Bundle Root 行为不变，也不复制真实 Profile。
2. **建档成功仍弹“操作未完成”**：实际堆栈是 `CoachPage.refreshPreview()` → `AppController._practice_context_preview()` → `build_practice_context_preview()` 的 `current Practice task is unavailable`。隐藏的 Coach 页在首题建立之前就请求预览。现在仅在页面可见且已有当前题目时读取；打开 Coach 后仍正常刷新预览。
3. **Codex 发现 / 握手成功，却没有下一问**：PATH 对应 Codex CLI `0.146.1`。将诊断窗口截止时间临时放宽后，获得真实终态错误：`The 'gpt-6-astra' model requires a newer version of Codex.` 原来的 30 秒硬超时和 `friendly_error()` 通用分支掩盖了这个原因。现在版本拒绝有明确中文说明，保留回答，并提供设置入口。
4. **收到正文时又被硬超时截断**：本机已有 VS Code Insiders 附带的 Codex `0.153.0`；仅在隔离应用设置中通过既有可执行文件配置选用它。实际连接发生五次重试，约两分钟后才开始返回文本。面试请求现在有 180 秒上限和“停止请求”按钮；超时关闭本应用拥有的传输，避免旧请求继续占用连接。没有新增自动重试框架或改动用户的模型 / 推理强度偏好。
5. **界面错位与误导**：全局浮条由固定 52px 改为按文字高度布局；入场弹窗使用深色遮罩；材料复选框允许换行；模型摘要与设置按钮上下排列；开始按钮使用既有 LabButton；没有 Session 时不显示“未知”计时状态。Codex 高压配置不再同时显示“缺少完整固定题，不能开始”，也不暗示当前动态路径会自动加入 Coding。
6. **失败仍显示绿色“AI 已连接”**：面试期间顶部读取结构化请求状态，分别显示响应中、重连、失败、已停止。停止使用现有 `turn/interrupt`，等实际终态后恢复操作；不从提示文字推断状态。协议核对参考 [官方 App Server 生命周期与中断说明](https://developers.openai.com/codex/app-server/)。

### 真实窗口操作结果

| 流程 | 实际结果 |
|---|---|
| 新目录 → 中文名称 → 后训练岗位 → No-AI | 正常建档并进入真实 `FND-001` 作答页；最终重验没有通用错误 |
| 关闭后同目录重启 | 恢复原档案，没有再次建档 |
| 首页“继续训练” → 首题 | 真实题面与本地 starter 可见，不是演示代码 |
| 后训练 / 实习 / 高压 / Codex → 确认上下文 | 立即进入本地开场题 `q-001`，尚未发送模型请求 |
| 锁定合成回答 → 再次确认发送 → 实际 Codex | **123.41 秒后收到成功终态，保存本轮证据并进入 `q-002`**；正式代码截止时间为 180 秒，没有诊断覆盖 |
| 再次重启 | 恢复同一 Session 的 `q-002`；真实问题询问按来源划分数据与近重复泄漏检查，回应了前一回答 |
| q-002 提交后发起请求 → 点击停止 | 取得真实 `turn/completed: interrupted`；从发起到终态 1.48 秒，停留 q-002，已锁定回答保留，没有生成假评分 |

用于诊断的两次截止时间覆盖明确不作为最终通过证据：旧 CLI 在约 112 秒返回版本拒绝；新 CLI 的首次诊断在 120 秒截止时仍在流式输出。随后才以正式 180 秒逻辑获得上述成功结果。网络重试开销没有被解决，不能承诺快速响应。

### 本轮定向测试

前缀均为 `.venv\Scripts\python.exe -m pytest`，没有运行完整 pytest。

| 参数 | 结果 |
|---|---|
| `tests/infrastructure/test_desktop_platform.py -k "source_data_override or packaged_workspace_accepts" -q` | 2 passed |
| `tests/infrastructure/test_ai_connections.py -k "codex_model_version_rejection or codex_protocol_error" -q` | 2 passed |
| `tests/infrastructure/test_interview_input_runtime.py -k "long_toast or answer_hint_hides" -q` | 3 passed |
| 同文件 `-k "nonexistent_practice or request_can_stop" -q` | 初次 2 failed / 1 passed；发现取消消息仍泛化，以及测试未持有 Qt window 包装器 |
| 同文件 `-k "nonexistent_practice or (request_can_stop and stop and not timeout)" -q` | 修订中 1 failed / 1 passed；取消提示已通过，测试窗口生命周期问题继续定位 |
| 同文件 `-k nonexistent_practice -q` | 单项修订两次失败（Qt 包装器生命周期、将 dict 当作 QJSValue），最终 1 passed；测试设置目录已显式隔离 |
| 同文件 `-k "geometry_at_supported_sizes or ui_lock_preview or (request_can_stop and not timeout)" -q` | 6 passed |
| `tests/infrastructure/test_desktop.py::test_interview_setup_uses_profile_role_availability_and_real_report -q` | 1 passed |

共 16 个不同的相关用例按上述分组最终通过，不把分组结果冒充全量通过。布局覆盖 900×620、1080×680、1280×800、1440×900，浅色 100% 与深色 125% 字体；获焦 / 中文组字提示、浮条自动高度、按钮可达、停止 / 超时保留回答、旧超时不影响新请求均有直接检查。`git diff --check` 通过。

真实窗口驱动位于 ignored 的 `workspace/maintainer/live-interview-20260905/drive.py`，实际调用参数包括 `--entry-only`、`--diagnose-timeout`、`--new-codex --diagnose-timeout`、无参数的正常请求、`--stop-request`、`--fresh-entry`、`--fresh-entry-final`。启动诊断初次报缺公共资产；驱动曾因 Popup 动画未结束漏点、已有面试时首页 CTA 已变化而中止，这些被修正为正常窗口操作，没有为驱动改动业务规则。

已查看的本地截图包括：

```text
workspace/maintainer/live-interview-20260905/07-current-question.png
workspace/maintainer/live-interview-20260905/08-answer-input.png
workspace/maintainer/live-interview-20260905/11-after-real-response.png
workspace/maintainer/live-interview-20260905/fresh-entry-final/06-setup-context.png
workspace/maintainer/live-interview-20260905/verified-ui/long-error-900.png
workspace/maintainer/live-interview-20260905/verified-ui/interview-900x620-dark-submit.png
```

前四项来自正常启动的隔离应用；`07` 是真实第二问重启恢复，`11` 是停止请求后的状态。`verified-ui` 来自定向测试，不代表实际账号连接。截图留在本机，不替换 README 发布截图。

### 未解决项与终局

- 本机 Codex 连接重试仍约两分钟；仅验证了已安装 `0.153.0` 与当前账号默认模型这一组合，不声称所有版本 / 模型可用。日常应用若仍选择旧 CLI，需从已提供的设置入口选择兼容版本；本轮没有偷偷修改用户的全局选择。
- 当前动态面试仍缺完整跨轮背景组装、阶段推进与自动 Coding 衔接；本轮只证明真实 `q-001 → q-002` 及恢复 / 停止。没有把局部可用冒充完整产品目标完成。
- 没有使用真实材料、真实 Keyring 条目，也没有验收完整评分报告、Windows 发布包或 macOS；未运行全量、RC CI 和打包。
- 所有既有用户未跟踪文件及 UAT 资料保留。源码与文档显式分批提交，ignored 问答、日志、截图与诊断脚本不进入 Git。

状态：`REAL_WINDOWS_CODEX_NEXT_QUESTION_VERIFIED / WAITING_FOR_USER_UAT`。

---

## 2026-09-05 更新：版本核对与输入 / 追问修复

本节保留本日较早的版本核对与 Fake 验证结果；后续真实交互以本文件顶部补充为准。后面的 2026-09-02 记录保留为历史证据。

### 版本差异

执行 `git fetch origin` 后核对，实施起点如下：

| 对象 | 提交 / 版本 | 与实施起点的关系 |
|---|---|---|
| 本地工作分支 `feature/product-v1-phase2-reliability` | `01f6b99836730d06fbf6b6a76c81b7942578db90` | 起点 |
| GitHub `origin/main` | `01f6b99836730d06fbf6b6a76c81b7942578db90` | 相同，左右差异 `0 / 0` |
| GitHub 旧同名 feature 分支 | `0bb0144` | 落后起点 88 个提交，包含合并历史 |
| 最新公开桌面 Release | `v0.4.0-alpha.3`，Tag 提交 `36db5ac` | 起点比 Tag 多 118 个提交 |
| 本地与远端 main 的 `pyproject.toml` | `0.4.0a3` | 版本号相同不表示与发布包源码相同 |

[公开 Release](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.3) 仍是 Alpha 预发行。因此，当前 UI 故障不能归因于“本地没有同步 GitHub main”；但下载的桌面包也不能当作当前 main 的构建。

本轮修复分支：`fix/desktop-input-interview-20260905`，源码提交 `59b63a9`。不移动 `main`，不更新 Tag 或发布包。源码的 `git diff --cached --check` 已通过；提交使用 `[skip ci]`，未创建会触发 CI 的 PR。

### 直接根因与修复

1. **输入提示重叠及基线错位**：实际使用的 PySide6 6.11.2 Material `TextArea` 带浮动标签与顶部 inset，和项目自绘背景、固定 padding 冲突。运行时测试在修复前捕获到输入框获焦后仍可见的 `FloatingPlaceholderText`。新增轻量 `LabTextArea` 使用 Qt Basic 的非浮动输入行为，保持既有主题，获焦就隐藏提示；文本、提示与光标共用内边距。面试回答、证据、追问、练习编辑器 / 复盘框和 Coach 输入接入同一控件。`LabTextField` 同样移除 Material 的浮动样式影响，不更改任何数据规则。
2. **普通 API 已追加下一问却弹出通用错误**：`AppController.assessInterviewWithProvider.complete()` 的动态分支保存一次评分并追加题目后，没有返回，又落入公共分支重复保存相同评分。补上该分支的 `return`；没有新增异常框架或更改评分规则。
3. **动态面试先自评造成无法继续**：旧界面优先展示自评动作，一旦完成自评，当前问题已被评估，继续请求 AI 的条件失效。动态模式改为单一继续路径：“提交并锁定回答 → 让 Codex 继续提问 / 生成下一问 → 确认发送”。只有固定面试保留原来的自评表单。不重写已有 Session 或清除历史评分。
4. **小窗口与浅色提交动作不清楚**：提交说明与按钮改为窄屏上下排列、宽屏左右排列；取消常驻整张题目卡的强调边框；计时与操作使用现有主题字体。语音操作按需展开。验证 900×620 时，主按钮可以完整滚动到视口内，不依靠缩小字体。
5. **题目切换后的旧草稿**：只有 Interview / Question 身份变化时才清空本地证据和追问草稿；切换导航不清空同题回答。原题已经提交的回答与评分仍保留在原题。
6. **上下文弹窗**：将本轮问题和已锁定回答的标签改为中文，统一确认按钮与深色遮罩，保留显式确认后才发送的边界。

### 定向验证与截图

运行环境：Windows 源码模式、Python 3.11.9、PySide6 6.11.2。测试使用正式 `Main.qml`、真实 Application Service 与临时独立学习档案，不使用 demo controller，不读取人工 UAT 档案或真实材料。外部 Codex / API 使用 Fake；这不是实际账号连接验收。

测试环境变量：

```powershell
$env:PYTHONPATH=(Join-Path $PWD 'src')
$env:PYTHONNOUSERSITE='1'
$env:PYTHONUTF8='1'
$env:QT_QPA_PLATFORM='windows'
$env:QT_QUICK_BACKEND='software'
$env:LLM_LAB_UI_EVIDENCE_DIR=(Join-Path $PWD 'workspace/maintainer/ui-20260905/after')
```

实际执行记录（均为定向测试，没有全量回归）：

| 命令（前缀均为 `.venv\Scripts\python.exe -m pytest`） | 实际结果 |
|---|---|
| `tests/infrastructure/test_interview_input_runtime.py -k "hint_hides or followups" -q`，修复前 | `2 failed, 1 passed, 4 deselected`：复现浮动提示与重复评分 |
| `tests/infrastructure/test_interview_input_runtime.py -q`，第一轮修复后 | `7 passed`；截图检查进一步发现窄屏操作行和浅色按钮问题 |
| 同文件 `-q`，加入交互与草稿测试后 | `1 failed, 8 passed`：交互测试没有等待模态对话框的退出动画完成 |
| `tests/infrastructure/test_interview_input_runtime.py::test_ui_lock_preview_codex_response_enters_next_question -q` | 定位时两次失败；改为等待弹窗实际关闭后 `1 passed`，未为此修改产品代码 |
| `tests/infrastructure/test_interview_input_runtime.py -k "geometry_at_supported_sizes or ui_lock_preview" -q` | `5 passed, 4 deselected` |
| 下方列出的 4 个既有测试节点 | `4 passed` |
| 同一个真实点击测试，完善弹窗后 | 一次因测试遗漏 QtQuick 类型导入失败；恢复类型导入后 `1 passed`，最后一轮为 `6.04s` |

4 个既有测试节点的实际命令：

```powershell
.venv\Scripts\python.exe -m pytest tests/infrastructure/test_onboarding_qml_hotfix.py::test_placeholder_is_removed_as_soon_as_user_text_exists tests/infrastructure/test_desktop.py::test_provider_assessment_scores_the_locked_answer_once tests/infrastructure/test_desktop.py::test_interview_setup_uses_profile_role_availability_and_real_report tests/infrastructure/test_desktop_design_system.py::test_deploy_specs_exactly_cover_the_qml_tree -q
```

9 个新增用例已按上述分组验证通过，另外 4 个既有兼容用例通过；不把这些分组结果冒充一次全量通过。覆盖：获焦、中文 IME preedit / commit、清空后提示恢复、草稿隔离、Provider 与 Codex 各自推进到 `q-003`、正式页面真实点击后确认上下文并展示 `q-002`、四种窗口尺寸及浅色 100% / 深色 125% 字体、主按钮滚动可达。

已实际查看以下正式页面截图，全部使用合成测试回答：

```text
workspace/maintainer/ui-20260905/after/interview-900x620-dark-submit.png
workspace/maintainer/ui-20260905/after/interview-1280x800-light.png
workspace/maintainer/ui-20260905/after/dynamic-answer-locked-dark.png
workspace/maintainer/ui-20260905/after/dynamic-answer-context-dark.png
workspace/maintainer/ui-20260905/after/dynamic-second-question-dark.png
```

截图保留在 ignored 维护者目录，不替换 README 的 Release 截图。`dynamic-*` 中连接状态和 AI 回复来自测试 Fake，不代表已验证真实 Codex 登录、网络、模型或额度。最初的 offscreen 探针有中文字体缺字，没有将它作为中文视觉通过证据；正式视觉检查使用 Windows Qt 平台窗口。

### 明确保留的风险与下一步

- **真实外部服务**：本轮未发送真实 Codex / API 请求，未使用用户材料；需实际账号完成“提交回答 → 下一问”UAT，不能据此宣称所有连接故障已修复。
- **完整动态面试语义仍未完成**：`build_role_interview_context_preview()` 包含岗位、级别、难度、当前题目技能标识和当前回答，但没有统一打包完整岗位技能说明、完整流程要求与所有前序回答。普通 API 每次请求尤其不能假定拥有之前的对话。`append_dynamic_role_question()` 当前只追加非代码追问；没有自动进入手撕的完整阶段调度。
- **历史中断会话**：已经被手动评分或已有部分落盘失败的旧 Session 未被自动改写。新流程避免再次陷入自评路径，但不声称恢复了任何已有真实会话。
- **空追问 / 上限**：模型不返回追问、达到 20 问上限等终止路径没有在本次 UI 修复中重做。
- 未运行完整 pytest、课程 Oracle、真实材料 / 真实 Keyring、macOS 实机、Windows/macOS 打包、RC CI；未创建 Tag、未发布 Release。
- 原有未跟踪产品文档、`test结果.md`、图标源文件、临时探针和 UAT 数据全部保留，不纳入源码修复提交。

当前裁决：`TARGETED_INPUT_AND_NEXT_TURN_CHECKS_PASSED / WAITING_FOR_MANUAL_INTERVIEW_UAT`。下一步优先验收真实账号的下一问，再单独处理完整流程和跨轮上下文，不能用本轮修复冒充完整动态面试已经实现。

---

## 历史记录：2026-09-02

更新时间：2026-09-02  
仓库：`E:\\hz-llm-interview-lab-codex`  
分支：`feature/product-v1-phase2-reliability`  
基线 HEAD：`8eefde9fdfe74be6ca330cb638e08c00a02268bf`

> 本报告只记录当前实现和人工验收发现。本轮按用户要求不修复下列两个问题，不构建 Windows/macOS，不运行全量回归。

## 一、当前实现概况

当前分支已经包含以下已提交前的源码修改：

- 动态面试首题路径：创建真实 `dynamic_ai` Session，仅持久化 `q-001` 本地开场题；
- 上下文确认弹窗：按“岗位技能与面试流程 / 求职意向与能力自评 / 授权材料”分行展示，材料 SHA 使用短摘要；
- Codex 面试官入口：支持连接、模型与推理强度配置的现有路径；
- 动态后续问题调用链：回答锁定并请求 Codex/Provider 评估后，只有返回非空 `follow_up` 时才追加一个下一问题；
- 异步操作的 Profile、Interview、Question、Operation ID 隔离和 busy 门控；
- Interview 页面确认弹窗底部按钮颜色和布局已改为深色主题一致；
- 启动运行时、错误状态、Schema 和针对性桌面测试已有相应变更。

## 二、人工验收发现（按要求暂不修复）

### 1. 输入框提示与实际输入重叠

**现象**：在回答框输入“我叫洪洲”或在评估证据框输入“aa”后，灰色提示仍停留在输入区域，与用户文字重叠，导致文字难以阅读；同时用户观察到文字基线/对齐不稳定。

**源码位置**：`src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml` 中的 `TextArea` 对象：

- `id: answer`（主回答）；
- `id: evidence`（回答证据）；
- `id: followupAnswer`（追问回答）；
- Coding 区的 `id: codingEditor` 也使用同一类编辑器样式。

这些控件当前依赖 Qt `placeholderText` 与 `padding` 的组合。截图证明当前实现没有满足“开始输入后提示立即消失、文本与边距一致”的用户可见契约。

**状态**：`OPEN / P0 UX`。本报告不修改实现。

### 2. 当前人工路径只看到一个问题

**源码事实**：

- `role_interviews.create_dynamic_role_interview()` 创建 Session 时只写入 `q-001`；
- `q-001` 的来源为 `process_opening`，标题为“自我介绍与经历概述”；
- 后续问题只能经由 `append_dynamic_role_question()` 追加；
- Controller 只有在当前回答已锁定、Codex/Provider 评估返回合法结果且 `follow_up` 非空时，才追加一个 `q-002`，并重新加载当前 Session。

**产品语义**：这不是“开始时生成完整题单”，而是一问一答的动态模型。首屏只有一个问题是当前设计的预期行为；但“回答后能否实际得到下一问”仍需要一次成功的 Codex/Provider 真实传输才能证明。

**人工验收状态**：本次截图/操作停留在首题或上下文确认流程，尚未取得成功的 `q-002` 证据。因此不能声称动态追问已经在真实 Codex 会话中可用，也不能把“只有一个问题”描述成已完成的动态面试体验。

**状态**：`OPEN / P0 FUNCTIONAL VERIFICATION`。按用户要求本轮不修复、不扩展题库。

## 三、测试与运行证据

本轮之前已执行的直接验证：

```text
.venv\\Scripts\\python.exe -m pytest tests/infrastructure/test_desktop.py -k "dynamic_interview_enters_with_local_opening or codex_dynamic_first_question or interview_setup_uses_profile_role_availability_and_real_report or standalone_runtime_seeds_public_assets" -q
5 passed, 33 deselected in 16.45s

QT_QPA_PLATFORM=offscreen .venv\\Scripts\\python.exe -m llm_interview_lab.desktop.main --smoke-test --window-size 1280x800
status: ok
```

真实隔离 Controller 探针曾得到：

```text
delivery_mode = dynamic_ai
interview.status = active
total_questions = 1
question_id = q-001
source.kind = process_opening
busy = false
```

本报告生成后没有再次运行测试，没有运行 `pytest -q` 全量，没有构建应用，没有触发 CI。

## 四、数据与未提交文件

当前工作树仍包含已有源码修改以及人工 UAT 目录。以下文件/目录被保留但不应进入源代码提交：

- `.uat-phase2-manual-0902/`、`.uat-luna-manual-0902/`、`.uat-luna-visual-0902/`：隔离 UAT 数据、日志和截图；
- `.tmp_controller_extract.txt`：临时探针文件；
- 用户提供的产品计划、反馈、评审和 `test结果.md`；
- `app-icon-quiet-forge-v1.png`：用户提供的原始图标资产。

这些文件没有被删除、覆盖或清理。源代码提交只包含已跟踪的实现/测试/Schema 修改，以及本报告和现有动态面试实施计划。

## 五、下一步（不在本轮执行）

1. 用 Fake Codex 或真实可用 Codex 完成一次“锁定 q-001 → 请求评估 → 追加 q-002”的定向验证；
2. 单独修复所有 `TextArea` 的 placeholder 可见性和文本边距对齐；
3. 在上述两项通过后，再由维护者进行人工 UAT，不以静态截图或单个 smoke-test 代替。

## 当前裁决

`WAITING_FOR_MANUAL_INTERVIEW_UAT`  
本报告记录了两个未修复问题；当前实现不能宣称“输入框体验已修复”或“Codex 动态多轮面试已完成”。
