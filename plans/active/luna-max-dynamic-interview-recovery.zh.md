# Luna Max 实施交接：动态模拟面试首问与确认弹窗可靠性

状态：`WAITING_FOR_MANUAL_INTERVIEW_UAT`

目标：修复“确认后卡在准备第一问”和上下文确认弹窗文字重叠，同时把实现收敛到用户要求的“一问一答、按回答逐步生成”的面试模型。

本文件是本轮唯一的实施计划和实验规程。它不是新的产品架构，也不授权扩展课程、岗位、Provider 或桌面技术栈。

## 0. 当前基线与安全边界

- 仓库：`E:\\hz-llm-interview-lab-codex`
- 分支：`feature/product-v1-phase2-reliability`
- 本次核对的 HEAD：`8eefde9fdfe74be6ca330cb638e08c00a02268bf`
- 当前工作树已有未提交修改；Luna Max 必须先保存快照，不能 reset、stash 后遗忘、覆盖或清理这些修改。
- 下列未跟踪内容属于既有用户/测试资料，不得提交或删除：`.tmp_controller_extract.txt`、`.uat-phase2-manual-0902/`、用户提供的计划/反馈文件、`test结果.md`、图标文件。
- UAT 只允许使用隔离 Profile `uat-manual` 和 `.uat-phase2-manual-0902` 数据根；不得扫描或读取其他真实 Profile。
- 本阶段不运行全量 pytest、不触发 CI、不构建 Release；只运行本文件列出的直接验证。

## 1. 已确认的事实与真实根因

### 1.1 用户看到的界面不是当前目标路径

截图中的文案包括“确认本场设置并生成第一问”“确认冻结 AI 个性化面试计划”“正在准备第一问”。当前分支的 `InterviewPage.qml` 已有不同文案（“确认设置并进入面试”“开始动态模拟面试”），并且当前 QML 的 `onInterviewPlanReady()` 已被改为空处理。由此可判定，截图所示窗口曾由旧源码/旧可编辑安装加载，不能拿它证明当前补丁已生效。

已观察到的进程事实：

- 一个入口从 `.venv` 启动，但子进程实际加载过 `E:\\llm-lab-wt-alpha4\\src` 的旧 editable 安装；
- 当前仓库的正确源码是 `E:\\hz-llm-interview-lab-codex\\src`；
- 因此第一项实验必须验证 `sys.executable`、`sys.path`、`llm_interview_lab.__file__` 和 QML 文件绝对路径，不能只看窗口标题或版本号。

### 1.2 卡住的直接技术根因

旧路径在开始面试时先向 Codex 请求“整场非代码问题计划”。App Server 可以发出 `sampling request timed out` / `willRetry=true` 等事件而长时间没有正常终止事件；旧 Controller 没有把 `method == "error"` 转成终态，所以 `busy` 一直为真，QML 只能显示“准备第一问”。

### 1.3 当前分支已经验证的可复用资产

当前工作树的 Controller/Domain 已包含以下可复用实现，Luna Max 不要重复造一套：

- `AppController.startDynamicPersonalizedInterview(...)`：校验上下文后同步创建动态 Session；
- `AppController._dynamic_opening_question(...)`：提供本地开场题“自我介绍与经历概述”；
- `AppController._finish_dynamic_initial_question(...)`：持久化并进入面试页；
- `ApplicationService.dynamic_interview_context(...)`：只构建当前获准上下文，不生成未来问题；
- `ApplicationService.create_dynamic_interview(...)` 与 `role_interviews.create_dynamic_role_interview(...)`：只写入当前问题；
- `append_dynamic_role_question(...)`：当前回答完成后一次追加一个后续问题；
- `source.kind = process_opening` 的 Schema/解析兼容；
- `runtime.PUBLIC_ASSET_REVISION = "role-interview-source-kind-v2"`：可避免旧 app-data Schema 阻塞新 Session；
- Codex 终态错误与超时的现有处理骨架。

一次真实的隔离 Controller 探针已经得到：

```text
preview_parts = 4
context_sha256 = present
interview.status = active
delivery_mode = dynamic_ai
total_questions = 1
question.title = 自我介绍与经历概述
question.source.kind = process_opening
busy = false
```

这证明“本地首问立即进入”在正确源码和隔离数据上可行；它不证明外部 Codex 的后续生成已在本机成功。

### 1.4 弹窗重叠的直接根因

旧弹窗用内容驱动宽度的 `StatusPill` 加长材料标签/完整 SHA 放在同一横向布局。窄窗口下 pill 的隐式宽度和文本宽度相互挤压，出现截图中的“将发送”覆盖标签、材料名和 SHA 串出界。确认面应是权限摘要，不应是日志转储。

## 2. 冻结的产品行为契约

### 2.1 启动契约

```text
选择岗位/难度/AI/材料
→ 显示上下文预览（只确认将发送什么）
→ 点击一次“确认进入面试”
→ 立即建立真实 Session
→ 立即显示第一问（固定流程开场题）
→ 候选人回答并锁定
→ 仅此时请求 Codex/Provider 评分和下一问
```

禁止在点击确认后等待整场计划、未来问题列表或完整蓝图生成。

### 2.2 AI 上下文契约

首个请求（如果实现为首问请求）只能包含：

1. 面试流程：自我介绍 → 项目/实习/论文拷问 → 八股 → 手撕；
2. 当前岗位对应的 canonical skills；
3. 难度/压力要求；
4. 用户明确授权的个人信息、简历/JD/材料快照；
5. 当前回合所需的最小对话状态。

不得包含：整个 Workspace、其他 Profile、Git 历史、Oracle、Private Tests、API Key、未授权材料或预生成的全部未来问题。

首问可以由本地流程直接提供，以保证可用性；这不是“假面试”，因为它会持久化到真实 Session，并且后续问题仍由 AI 根据实际回答逐问生成。若产品决定让模型生成首问，也必须先创建 Session/显示可取消的非阻塞状态，超时不得阻塞进入；本阶段推荐先采用本地开场题方案。

### 2.3 问题生命周期

每个问题必须只有以下状态之一：

```text
created → answering → locked → assessed → next-question-created
```

- Session 创建时只有 `q-001`；
- `q-001` 的 `source.kind` 为 `process_opening`；
- 后续 `q-N` 只能在上一问回答锁定后由 Codex/Provider 生成并追加；
- 任何异常都进入可重试终态，不保留无限 busy；
- Coding 题继续由本地 Catalog/Grader 决定，不让 AI 捏造题目或测试。

### 2.4 “检测到 Codex”不等于“可以完成请求”

至少分成三种展示状态：

```text
未发现：没有找到可执行文件
已发现：找到可执行文件，但尚未验证会话
可用：thread/turn 建立并收到可解析终态
```

`shutil.which()`、常见路径探测或进程存在只能产生“已发现”，不能显示“AI 已连接”。只有真实连接测试成功才可设置 `ready=true`。请求超时、401、重试耗尽必须显示具体下一步，同时不影响本地首问和 No-AI 刷题。

## 3. 实施范围与文件所有权

### Slice U：确认弹窗和入口（唯一修改 QML）

允许文件：`src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml`，必要时才改 `Main.qml` 的 Toast 位置。

要求：

1. `startConfiguredInterview` 只调用 `openPersonalizedPlanContext()`；不得调用旧的全场计划生成函数。
2. `onInterviewPlanReady()` 保留兼容符号也可以，但不能打开旧的全场计划 Dialog。
3. `planContextDialog` 使用显式几何：
   - 宽度 `min(600, max(420, parent.width - 40))`；
   - 内容区域 `clip: true`；
   - 每行 `width = list.width`，高度 40–56；
   - 状态点/勾选标记固定 18–24px；
   - 标签列 `width = max(0, row.width - 48)`；
   - 标题最多两行，`wrapMode: Text.Wrap`；长文本 `elide` 或换行，不能让隐式宽度决定父布局；
   - 材料 SHA 只显示短摘要（例如前 8 位），单独一行；不要在主行放完整 SHA；
   - 列表和按钮之间至少 24px 安全间距；
   - 空上下文显示明确错误，不打开空白确认框。
4. 行文案使用自然中文，例如“将发送：岗位技能与面试流程”“将发送：授权材料（已获本场许可）”，不要出现“英文原始契约”。
5. 确认按钮在提交期间禁用，文本变为“正在进入面试…”；取消按钮仍可用，不能用全局 Toast 替代表单内错误。
6. 页面只展示一个主 CTA；去掉或隐藏旧的“冻结计划”按钮和任何无行为控件。
7. 选择器、checkbox 和 Dialog 必须有稳定 `objectName`，但不要给每个装饰 Rectangle 添加测试对象名。
8. 检查 `selectedRole`/当前 role 不为空；不能使用 `roles[3]` 之类的隐式默认。

验收截图：正确源码运行下至少生成 1280×800 和 900×620 的确认面；检查无重叠、无裁切、中文可读、按钮可点击。

### Slice C：动态首问 Controller（唯一修改核心 Python）

允许文件：`src/llm_interview_lab/desktop/controller.py`、必要的 `application.py`/`role_interviews.py` 局部、对应 Schema 测试。

要求：

1. 输入顺序：验证 `profile_id/role_id/seniority/difficulty/ai_mode/material consent/context SHA` → 再写 Session/Profile。
2. 成功路径必须同步返回或发布结构化状态：

```json
{
  "status": "started",
  "interview_id": "...",
  "question_id": "q-001",
  "source_kind": "process_opening",
  "operation_id": "..."
}
```

3. 已有同一 `operation_id` 的重复点击不得创建第二个 Session。
4. 本地创建/写入失败时清除 busy、保留可重试输入、记录脱敏日志；不得吞掉 traceback，也不得把所有错误压成 generic Toast。
5. 首题打开失败时：
   - Session 若已成功持久化，导航到首页并显示可操作提示；
   - 不回滚或删除用户 Profile；
   - 日志记录阶段（validate/create/start/load/navigate）和错误编号。
6. Provider/Codex 的后续请求必须处理：正常终态、`error` 事件、取消、超时、重试耗尽。任一终态都要把 `busy` 设回 false。
7. 异步回调必须核对 `(profile_id, interview_id, question_id, operation_id, context_sha256)`，旧回调不得覆盖新题。
8. 只调用 `append_dynamic_role_question()` 追加一个问题；禁止恢复“先生成全场列表”的 GUI 路径。

不得引入全局异常层、事务框架、第二套 Provider、数据库或大规模 Controller 拆分。

### Slice R：运行时/进程来源修复（仅在实验确认需要时）

允许文件：`src/llm_interview_lab/desktop/main.py`、`runtime.py`、打包入口配置；不得借机重写 Windows/macOS 打包。

要求：

- 启动日志最早记录解释器、源码根和 QML 根；
- 正式入口必须使用当前安装环境的 editable source，不得静默加载另一个 worktree；
- 若检测到 QML 与 Python 源码不属于同一仓库，显示可见错误并写 bootstrap 日志；
- 不把用户绝对路径写入普通日志，诊断导出时才允许脱敏展示；
- 不为 UAT 增加专用 Launcher。

### Slice T：直接测试（唯一修改测试文件）

允许文件：`tests/infrastructure/test_desktop.py` 或已有直接相关测试文件。

最小测试集合：

1. QML 静态契约：入口不调用旧全场计划；Dialog 行有显式宽高；旧“正在准备第一问”文案不可达。
2. Controller：无 Codex transport 时，合法配置创建真实 dynamic Session，只有 q-001，且 `busy=false`。
3. Controller：重复点击只产生一个 Session/operation。
4. Controller：Codex `error`/timeout 终态清除 busy，并返回可操作中文消息。
5. Controller：Profile/题目切换后旧异步结果不会覆盖当前状态。
6. Schema：`process_opening` 可读写；旧 app-data revision 会安全同步公共 Schema。

每个 Slice 只运行自己范围的定向测试；不要为了“保险”重复全量。

## 4. 实验顺序（必须按顺序，避免再次误判）

### E0：进程和源码归属实验

在启动任何 GUI 前，记录并核对：

```powershell
$repo = (Resolve-Path '.').Path
$env:PYTHONPATH = Join-Path $repo 'src'
$env:PYTHONNOUSERSITE = '1'
.venv\Scripts\python.exe -c "import sys, llm_interview_lab; from pathlib import Path; print(sys.executable); print(Path(llm_interview_lab.__file__).resolve()); print(Path('src/llm_interview_lab/desktop/qml/Main.qml').resolve())"
```

验收条件：`llm_interview_lab.__file__` 必须在当前 repo 下；若不是，先修环境/入口，不得继续看截图。

启动后再用 `Get-CimInstance Win32_Process` 检查父子进程的 `ExecutablePath` 和 `CommandLine`。同一时间只保留一个目标 GUI 窗口，关闭此前从其他 worktree 启动的窗口。

### E1：隔离 Controller 探针

使用全新临时目录（不触碰用户真实目录），只创建 `uat-manual` Profile。调用现有 `dynamicInterviewContextPreview()` 和 `startDynamicPersonalizedInterview()`，仅输出：

```text
profile_id / role_id / ai_mode
preview part count / context SHA 是否存在
interview_id / status / delivery_mode
question count / question id / source kind
busy / page
```

通过条件：`active + dynamic_ai + q-001 + process_opening + busy=false`。若失败，记录发生在 validate、create、start、load 还是 navigate，不得先改文案。

### E2：确认面截图实验

用 E1 的真实隔离 Profile 加载正式 QML，设置岗位、实习级别、高压、Codex 和“本场授权材料”，打开确认面。捕获：

```text
1280×800
900×620
浅色
深色
```

人工检查：每行边界、标签列宽、材料摘要、按钮安全距离、Dialog 是否可滚动；禁止只检查 PNG 文件大小。

### E3：真实点击链路实验

在同一窗口点击一次确认，不进行第二次点击。5 秒内应出现真实“自我介绍与经历概述”问题和回答区域。检查持久化 Session 的 `questions` 长度为 1。退出并重新打开同一数据根，确认仍是同一个 `interview_id` 和 q-001，不重复创建。

### E4：Codex 后续回合实验（Fake 优先）

先注入 Fake App Server，而不是直接依赖付费/登录服务：

1. 锁定 q-001 回答；
2. Fake stream 返回一条合法下一问 JSON；
3. 断言只追加 q-002；
4. Fake stream 返回 `error`、超时和取消各一次；
5. 每次都断言 `busy=false`、当前问题不被清空、界面有重试入口。

真实 Codex 只能作为附加实验。若出现 `sampling request timed out`、401 或重试耗尽，报告“传输不可用”，不能把“已发现”改写为“已连接”，也不能阻塞首问。

### E5：旧路径回归扫描

只在当前 QML 和直接测试范围内搜索：

```powershell
rg -n "生成整场|冻结.*计划|正在准备第一问|generatePersonalizedInterviewPlan|onInterviewPlanReady" src/llm_interview_lab/desktop/qml tests
```

允许兼容 API 和测试中保留符号，但必须证明正式 GUI 入口不可达；若仍可从主 CTA 触发，视为 P0 未通过。

## 5. 验收矩阵

| 场景 | 预期结果 | 证据 |
|---|---|---|
| 正确源码启动 | Python/QML 都来自当前 repo | E0 输出、启动日志 |
| 确认弹窗 1280×800 | 文本不重叠，按钮可见 | 截图 |
| 确认弹窗 900×620 | 列表可滚动，底部 CTA 不被遮挡 | 截图/点击 |
| Codex 未登录 | 说明可操作，但本地首问仍可进入 | UI + Controller 探针 |
| Codex 请求超时 | 30 秒内终态，busy 清除，有重试 | Fake/日志 |
| No-AI 刷题 | 不受 Codex 失败影响 | 直接测试 |
| 合法开始 | 一个真实 active Session，只有 q-001 | session 文件/Controller 输出 |
| 重复点击 | 不产生第二个 Session | operation_id 测试 |
| 锁定首问回答 | 才触发下一问请求 | Fake stream 调用记录 |
| 切换 Profile/题目 | 旧结果不覆盖当前页 | 隔离测试 |
| 重启 | 恢复同 Profile、同 Session、同题 | E3 |
| 未授权材料 | 不进入上下文、不发送 | context preview + 日志 |

任何一个“停在 busy、显示旧计划、Dialog 重叠、错误无下一步、首题不落盘”均为 P0，不得进入视觉打磨或发布。

## 6. 代码 Review 清单（Luna Max 完成后由 Main 独立审查）

- [ ] 是否误把旧 worktree/旧 editable 安装当成当前代码？
- [ ] 是否仍有主按钮触发整场计划？
- [ ] 是否把 `detected` 当成 `ready`？
- [ ] 是否存在 QML `StatusPill` 隐式宽度、无 width/height 的 delegate 或长 SHA 主行？
- [ ] 是否在 QML 重新实现 Profile、权限、解锁或 Session 规则？
- [ ] 是否先写 Profile/Session 后验证输入？
- [ ] 是否吞掉真实异常或只改成 generic Toast？
- [ ] 是否有重复点击、重复线程或重复 Session？
- [ ] 是否核对 profile/interview/question/operation identity？
- [ ] 是否让 Codex 错误阻塞本地首问？
- [ ] 是否泄露材料正文、答案、Oracle、Private Tests 或 Key？
- [ ] 是否顺手改动 Catalog、DAG、Interview 状态机或 Provider 架构？
- [ ] 测试是否只覆盖直接故障，而非无意义扩张？

## 7. 交付格式（Luna Max 每次只返回这一页结构）

```markdown
## 根因
- 只写已由日志、源码或可复现实验支持的根因。

## 修改文件
- 文件：符号/对象：改动目的。

## 关键实现
- 首问如何进入；
- 未来问题何时生成；
- 错误如何终止 busy；
- 弹窗如何避免隐式几何。

## 目标测试命令
- 只列本 Slice 的命令。

## 测试结果
- 逐条写通过/失败和耗时；不得写“应该通过”。

## 截图 / 日志位置
- 绝对路径或仓库相对路径；说明是否合成、是否隔离。

## 未解决风险
- Codex 外部传输、未验证平台等必须如实列出。
```

## 8. 给 Luna Max 的可复制任务提示

```text
你负责实现“动态模拟面试首问与确认弹窗可靠性”最小修复。

先执行 E0，证明 Python、QML 和当前仓库一致；若不一致先报告，不要修改业务代码。
只使用隔离 Profile uat-manual，不读取其他 Profile，不提交 UAT 数据。

产品契约：点击确认后立即创建真实 dynamic_ai Session，只持久化 q-001 的本地流程开场题“自我介绍与经历概述”；用户锁定回答后，才让 Codex/Provider 生成一个下一问。绝不能在开始时生成或展示整场未来问题计划。Codex 检测、连接成功和请求可完成必须分开；超时/error/取消必须清 busy 并给出可重试中文提示。

UI 契约：上下文确认 Dialog 使用显式宽高和有界文本；一行一个授权项；短 SHA 单独一行；不使用内容驱动 StatusPill 挤压标签；900×620 和 1280×800 不重叠、不裁切。自然中文使用“将发送：岗位技能与面试流程/授权材料”，不要写“英文原始契约”。

文件白名单：
- QML：src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml（必要时 Main.qml）；
- Core：src/llm_interview_lab/desktop/controller.py，必要时 application.py/role_interviews.py 的最小局部；
- 测试：tests/infrastructure/test_desktop.py 的直接测试；
- 只有 E0 证明入口污染时才改 desktop/main.py 或 runtime.py。

禁止：全局异常框架、事务系统、第二套 Provider、Catalog/DAG 修改、动态面试大重写、完整回归、构建 Release、删除用户文件、吞掉异常、把检测到 Codex 显示成已连接。

按 E1→E2→E3→E4→E5 顺序实验。每个 Slice 只跑直接测试；不要运行 python -m pytest -q。完成后严格按“根因/修改文件/关键实现/目标测试命令/测试结果/截图或日志/未解决风险”返回，不写长泛化报告。
```

## 9. 终局定义

本计划完成的终局不是“Codex 一定能在任何机器生成答案”，而是：

1. 正确源码启动后，第一次点击确认能进入真实第一问；
2. 弹窗在目标尺寸下清晰可读；
3. 后续问题严格按回答逐问生成；
4. Codex 不可用时首问、本地训练和 No-AI 仍可用；
5. Codex 可用性、请求失败和重试状态诚实显示；
6. 重启和异步回调不会串 Profile、题目或 Session；
7. 所有证据来自隔离真实数据和直接测试，不用旧截图、合成计划或“理论可用”表述。

完成后停止在：`WAITING_FOR_MANUAL_INTERVIEW_UAT`。不要自动进入 Phase 3、动态面试大重构、官方答案或发布流程。
