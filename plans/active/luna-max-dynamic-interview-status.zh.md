# Luna Max 动态面试当前状态报告

## 2026-09-05 更新：版本核对与输入 / 追问修复

本节是当前状态；后面的 2026-09-02 记录保留为历史证据，不再代表最新修复状态。

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
