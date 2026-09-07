# Luna Max 动态面试当前状态报告

## 2026-09-07：AI 仅用于面试、针对性追问与本地选题（最新）

基线 `1940add3fbe659bf2ba48d3b5056d07dfa37e4ac`，沿用 `fix/dynamic-interview-full-flow-20260905`。当前源码变更，不代表安装包或 Release 已更新。

实现提交：`2e1ae73`（面试策略与本地选题）、`04a6eb8`（删除 AI 辅助页、连接就绪状态及界面验证）。本轮全部提交使用 `[skip ci]`，保留现有未跟踪文件，不改写历史。

### 实际修改

- 删除正式 `CoachPage.qml`、导航、练习页 AI 面板/Drawer 及入口；连接页仅提供 Codex 面试官，不再显示教练/仓库代理模式。原页面可从 Git 历史恢复，用户教练历史和原有 CLI 不删除。
- 新增真正发送给模型的 [`dynamic-interviewer.md`](../../coach/prompts/dynamic-interviewer.md)，配合 `interview_flow.py` 的八岗位关注点与三档难度。先听完整经历再深入，不把简历细节当作已经回答；不知道或非本人负责时换角度，保持单个主问题、专业语气，不预生成题单、不补造经历。
- AI 返回不存在/空题号时，旧实现直接抛 `RoleInterviewError`，卡在已锁定的回答。现在仅从本地可运行、已经验证的候选里按已讨论技能和岗位权重更正；合法题号保留。更正写入当前 Session 时间线，并在题面上方提示。缺少题面、starter 或公开测试的节点不入池；无题可做时明确保留代码环节缺失，不虚构题目或通过记录。
- 真实运行发现材料导入会重建连接列表，误把刚测试成功的连接清回 No-AI。现在同档案、同配置的成功测试状态可跨刷新保留；重新保存（含换 Key）及换档失效。只用结构化 `ready`，不以“已连接”字样推断。
- README、桌面/连接文档和打包 QML 文件清单已同步；不改课程、评分、Mastery 或 Provider 架构。

### 真实交互与质量审查

使用正式 `desktop.main` / AppController / QML，在 Windows 上以鼠标和中文输入事件操作；合成后训练实习经历与 JD，未读取真实 Profile/简历。连接和材料准备由隔离脚本调用真实服务，提交由真实按钮触发。没有 demo controller 或假 AI 返回。

- DeepSeek 先做两轮策略实验，每轮四次提交均成功，但仍有问题堆叠/重复，**未据此通过质量验收**。随后将策略移到明确的面试指令，并强调“简历不算已口头介绍”、一轮一个重点和换角度。
- 最终策略四次真实接续：`q-001 → q-005`，耗时 **6.06 / 3.42 / 3.75 / 4.45 秒**。先邀请介绍经历；随后问去重边界；候选人表示不了解后转向其实际写过的脚本。
- 连接状态修复后再验证两轮：**3.84 / 4.31 秒**，刷新后 `ready=true`。实际下一问先邀请介绍本人核心工作，再围绕回答中的 chosen/rejected 检查追问具体例子。
- Codex `gpt-5.6-sol / low` 两轮均成功，同一 Thread；问题为“那就从星舟竞赛讲起……”及“你具体是怎样按用户划分训练集和留出集的？”。耗时 **123.84 / 14.62 秒**；第二轮没有重新创建面试线程。首轮慢仍未解决。
- 真实场次没有作答/验证代码，本次均如实保存为 `incomplete`；手撕错题号更正、真实题面及 starter 的打开使用确定性定向测试验证，不冒充真实 AI 曾返回错误 ID。

本地证据在 ignored 的 `workspace/maintainer/interview-focus-20260907/`：`strategy-`、`refined-` 为前两版，`final-live-result.json` 为最终四轮，`codex-live-result.json` 为 Codex，`ready-live-result.json` 为连接修正后两轮。已逐图查看 `ready-live-experience-dark.png`、`ready-live-small-light.png`、`ui-final/coding-corrected-question.png` / `coding-corrected-editor.png`。真实窗口尺寸为逻辑像素，Windows 缩放导致 PNG 物理像素更大。

### 实际目标测试

均使用仓库 `src` 作为 `PYTHONPATH`；以下 `python` 均指 `.venv\Scripts\python.exe`，GUI 使用 `QT_QPA_PLATFORM=windows`。仅目标测试，未调用全量回归。

```text
python -m pytest tests/infrastructure/test_dynamic_interview_flow.py -k unknown_coding_suggestion -q
修复前：2 failed，复现不存在/空题号直接抛错。

python -m pytest tests/infrastructure/test_dynamic_interview_flow.py -k "coding_suggestion or runtime_assets or invalid_ai_stage or context_keeps" -q
6 passed, 6 deselected in 18.37s

python -m pytest tests/infrastructure/test_interview_input_runtime.py -k "corrected_coding or onboarding_does_not_preview or shell_setup_home_and_settings or small_home_keeps" -q
首次：5 passed / 1 failed；新增测试误用了不存在的属性名，已改为实际 coding_text，不修改产品来迎合断言。

python -m pytest tests/infrastructure/test_dynamic_interview_flow.py tests/infrastructure/test_interview_input_runtime.py -k "conversation_strategy or corrected_coding or ui_single_submit_codex_response or single_submit_provider" -q
5 passed, 57 deselected in 27.84s

python -m pytest tests/infrastructure/test_dynamic_interview_flow.py -k "not full_flow" -q --tb=short
13 passed, 1 deselected in 48.89s

python -m pytest tests/infrastructure/test_chinese_docs.py tests/infrastructure/test_desktop_design_system.py tests/infrastructure/test_training_foundations_readme.py -k "all_readme_relative_links or gui_and_provider_user_terms or deploy_specs_exactly or readme_ai_is_interview_only or shell_breakpoints" -q --tb=short
5 passed, 38 deselected in 0.31s

python -m pytest tests/infrastructure/test_interview_input_runtime.py tests/infrastructure/test_desktop.py -k "material_refresh_keeps or resaving_same_connection or corrected_coding or demo_controller_exposes or home_and_practice_expose or shell_setup_home_and_settings" -q --tb=short
7 passed, 82 deselected in 31.30s

python workspace/maintainer/interview-focus-20260907/live.py
DeepSeek：UAT_TURNS=4，分别使用 strategy-/refined-/final- 标签；修正连接后 UAT_TURNS=2、ready-。
Codex：UAT_PROVIDER=codex、UAT_TURNS=2、codex-。

git diff --check
通过；仅 Git 行尾规范化提醒。
```

### 未运行与剩余风险

- 未运行完整 pytest、课程 Oracle 全量、Windows/macOS 构建、RC/CI；未创建 Tag/Release，未合并 main。
- 真实模型验证只覆盖合成后训练实习经历、DeepSeek Flash 关闭思考与 Codex low。八岗位/三档强度的上下文由测试覆盖，未把所有组合逐个付费实测。
- 提问措辞仍有模型波动，个别表述仍可能包含补充询问；没有承诺始终像真人。经历/原理各最多四问的现有流程边界不变。
- Codex 首轮高延迟、Windows `MS Sans Serif` DirectWrite 告警仍存在。本轮没有 QML 加载/绑定错误，不据此宣称 macOS 实机已经验证。
- 未删除真实材料、Profile 或已有未跟踪文件。截图/日志/合成 Session 不提交；Key 只用指定验收连接的系统 Keyring，不写源码、报告或命令。

状态：`WAITING_FOR_MANUAL_INTERVIEW_UAT`。

## 2026-09-07：DeepSeek、Codex 连续会话与中文题面（前一切片）

基线 `428efd63a6edfcf733938c1ee9b1a3d688fa7a3e`，主要实现提交 `0d3f0b24595c6ae6c5c937a68d9f57c2a17c68bc`、控件中线收尾提交 `29d8eaaeb8ce89a411369149380240b113b72637`；沿用 `fix/dynamic-interview-full-flow-20260905`。以下证据仅针对当前源码，不表示已更新任何安装包。

### 已解决的实际问题

- **重复标题与“详情”**：移除无必要的详情入口和弹窗；顶部只显示问次、计时和暂停，标题不重复。连接选择与材料授权移入回答区；正文、回答、操作区仍独立布局和滚动。综合评分及证据计算未变。
- **Codex 每轮新建线程**：原代码复用 App Server 进程，但每个答案都 `thread/start`，意在隔离撤销的材料。改为按进程、Profile、面试、模型与材料/背景 SHA 范围复用；范围变化仍新建线程，不把旧材料带回新请求。
- **QML 告警**：十个页面自定义 `palette` 与 Qt 基类属性冲突，统一改成 `colors`。Qt 控件自己的 `palette.buttonText` 保留，未用日志过滤掩盖问题。初次机械替换漏掉了部分原生赋值，真实 QML 加载测试失败后已全部纠正。
- **DeepSeek**：沿用现有 HTTP/SSE 适配器，官方地址、模型选择、自定义模型 ID、关闭/低/高/最高思考、保存并测试均可操作。普通 API 的就绪状态也用于顶部状态，不再已连接却显示 No-AI。Key 只进入 Windows Credential Manager，没有明文后备。
- **真实返回格式差异**：首次请求成功抵达服务，但 DeepSeek 将“空 coding_problem_id”返回为 `null`，被本地校验拒绝。已明确空字符串约定，动态请求附现有 JSON Schema 并启用 JSON 格式；没有放宽评分/题目校验。忽略思考片段，只解析回答正文；空正文和截断不伪装成功。
- **英文手撕题**：面试原来直接展示冻结英文 task，绕过中文展示。现在当前 45 份本地题使用中文要求，保留原函数签名与代码示例；可查看英文，设置语言变化也会生效。中文展示绑定原文 SHA，历史原文不同则明确提示，不改 Catalog、Session 题目或 Grader。

### 真实 Windows / 远程调用

使用生产 `desktop.main`、真实 AppController/QML、鼠标点击与中文输入事件。数据位于 ignored 的 `workspace/maintainer/deepseek-polish-20260907/`；全部为合成简历/JD和答案，没有读取或发送真实用户简历，没有使用 demo controller。连接/材料准备由隔离探针调用真实服务，回答与提交由真实控件驱动。

| 路径 | 结果 | 提交到下一问耗时 |
|---|---|---|
| DeepSeek v4 Flash，关闭思考 | 连续 9 次成功接续，进入 `FND-002` 中文手撕题 | 5.45、6.06、6.24、7.22、7.53、7.11、6.86、6.51、7.41 秒 |
| DeepSeek 布局/追问措辞收尾后 | 两轮均成功；问题引用合成经历中的偏好数据、去重与泄漏 | 4.52、6.81 秒 |
| Codex `gpt-5.6-sol` / low | 两轮均成功，同一 Thread，第二轮没有 `thread/start` | 126.62、13.44 秒 |

Codex 本地 `initialize` 0.125 秒，连接线程 0.235 秒、面试线程 0.250 秒，两次 `turn/start` 为 0.062 / 0.094 秒。首轮等待主要不在本地初始化；历史同日探针曾记录上游 `responseStreamDisconnected / request timed out` 和自动重试。**本轮只证明同场线程复用和真实接续，不能保证 Codex 首轮延迟已经解决，也不能将不同客户端、模型及账号的耗时直接比较。**

当前真实手撕只验证了进入中文题面，未填写代码或运行 Grader。本轮场次均按实际证据保存为 `incomplete`，没有宣称完成一场全环节通过的面试。高推理强度和 Pro 模型没有逐个付费实测，模型 ID 来自官方与真实 `/models`，参数通过 HTTP/SSE 定向测试。

### 截图与输入验证

截图存于上述 ignored 目录，不将账号配置、Session 或原始日志提交 Git。已实际查看：

- `refined-live-experience-dark.png`：真实 DeepSeek 下一问，紧凑连接/授权区；
- `refined-live-small-light.png`、`refined-live-small-dark.png`：900×620、125% 字号，题目滚动与主动作；
- `refined-live-connections-dark.png`：真实连接就绪，首屏模型/推理/Key 表单；
- `live-coding-chinese-dark.png`：9 次真实接续后到达的中文本地题；
- `screenshots/coding-chinese-dark.png`：最终源码的中文/英文切换检查（问题由隔离测试推进，不当作远程 AI 证据）。
- 最后逐图检查发现模型选择与材料勾选的控件中线仍有偏差，已统一高度；`screenshots/composer-aligned-dark.png` 和实际坐标断言验证修正。连接测试的合成就绪状态不作为账户可用性的证据。

四种窗口 900×620、1080×680、1280×800、1440×900 的定向 QML 测试覆盖深浅色及 100%/125% 字号、正尺寸、不重叠、IME 组字与提交按钮可见。`engine.warnings` 检查没有 QML 绑定或属性加载错误。

### 实际收尾测试

以下命令均设 `PYTHONPATH=<仓库>/src`，GUI 使用 `QT_QPA_PLATFORM=windows`；API 单元测试使用 Fake HTTP/Mock Keyring，不访问真实账户。

```text
.venv\Scripts\python.exe -m pytest tests/infrastructure/test_deepseek.py tests/infrastructure/test_ai_connections.py -q --tb=short
30 passed in 3.51s

.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k "deepseek_connection or codex_reuses or single_submit_provider or answer_geometry_at_supported_sizes or removes_details" -q --tb=short --junitxml=workspace/maintainer/deepseek-polish-20260907/target-results.xml
8 passed, 40 deselected in 47.53s

.venv\Scripts\python.exe -m pytest tests/infrastructure/test_deepseek.py tests/infrastructure/test_interview_input_runtime.py tests/infrastructure/test_desktop_design_system.py tests/infrastructure/test_alpha4_home_p1.py -k "current_chinese or deepseek_connection or shell_breakpoints_and_exercise_route or compact_evidence_rail" -q --tb=short
4 passed, 77 deselected in 9.64s

.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k deepseek_connection -q --tb=short
最后的中线对齐 + 模型/推理/Keyring + 中文切换：1 passed, 47 deselected in 11.99s

.venv\Scripts\python.exe -m pytest tests/infrastructure/test_chinese_docs.py -k all_readme_relative_links -q --tb=short
1 passed, 9 deselected in 0.19s

.venv\Scripts\python.exe workspace/maintainer/deepseek-polish-20260907/live.py
DeepSeek 9 轮；UAT_TURNS=2 + UAT_CAPTURE_LABEL=refined- 复测 2 轮
UAT_PROVIDER=codex + UAT_TURNS=2 + UAT_CAPTURE_LABEL=codex-：Codex 2 轮

git diff --check
通过（仅行尾规范化提醒，没有空白错误）
```

开发中曾针对首次 QML 失败重跑失败案例，并做相关连接/几何的选择测试；没有运行完整 pytest，没有 Windows/macOS 打包，没有触发 CI/Release。早期一组选择测试的完整输出未保留，未将其计入上述通过数。

### 仍然存在的限制

- Windows 仍出现一次 `MS Sans Serif` 的 DirectWrite 字体兼容告警；运行与真实答题可继续。剪贴板占用重试也不等于 AI 失败。本轮没有屏蔽这些系统日志。
- Codex 首轮 126.62 秒的长等待未消失；线程复用不能保证上游响应速度。
- 新题面翻译需随公开原文更新；历史场次可能需要查看英文原题。
- 未做 macOS 实机、全量回归或打包验证；公开安装包不包含本轮更新。
- 用户此前贴出的凭证未写入源码、报告或截图；建议在服务控制台轮换。真实测试凭证仅留在隔离测试档案的系统密钥环引用中，不自动复制到其他档案。

工作树原有未跟踪反馈、原图、计划和 UAT 目录全部保留。终局仍为 `WAITING_FOR_MANUAL_INTERVIEW_UAT`。

---

## 2026-09-07：面试界面视觉收敛（历史）

基线 `c904b3ef830422805205fc9e51f63dbf88a9ca11`，分支 `fix/dynamic-interview-full-flow-20260905`。本轮落实用户要求的布局与美观迭代，不修改 Controller、AI 传输、阶段、题库、评分或个人数据。

### 可见变化

- **准备页**：统一阅读宽度，按“面试目标 / 面试官与背景”分组；“开始面试”保持单一主动作并固定在底部。小窗口明确提示下方还有设置，细滚动条持续指示内容范围。
- **作答页**：题目与回答分别滚动，输入、发送范围、语音和提交收拢为一体式回答区。短回答不占满一块大框，长回答自动增高至上限后滚动；仍然只点一次“提交并继续”。低饱和焦点环和主题实色保留。
- **复盘页**：以分数、完成情况和逐条证据组织内容，去掉嵌套边框与重复标题。显示分数尺度、来源、置信度和未完成状态，不改变分值计算。
- **侧栏**：减轻未选中图标与分组标题的强调，档案区改为首字头像和两行摘要；导航和档案入口不变。

### 真实交互发现与修正

首次检查长回答时，光标移到末尾后没有随输入滚动：新增测试真实失败。改为移动整个 ScrollView，保留 TextArea 作为它的直接内容，由 Qt 处理输入光标和滚动，不另造编辑器逻辑。参考 [Qt TextArea 的滚动用法](https://doc.qt.io/qt-6/qml-qtquick-controls-textarea.html#scrollable-textarea)。

第二轮实看发现自定义细滚动条仍须明确右侧位置和完整轨道高度；已补几何断言。组合交互测试还暴露出展开语音时定位早于布局更新，导致录音入口落在视口外；现在先更新当前 Column 布局，再定位语音区域。工具检查确认查看发送范围不会锁定回答或发送请求，展开/收起语音也不会丢失草稿。

### 定向验证与证据

全部界面测试使用 Windows `QT_QPA_PLATFORM=windows`、正式 Main.qml、真实 AppController 与 Session 持久化；QSettings、档案和模型回复均隔离。**模型回复是 Fake Codex / fixture，不是本轮真实云服务实测。**没有读取用户简历、其他真实档案或 Keyring。

使用统一前缀 `.\.venv\Scripts\python.exe -m pytest`，`PYTHONPATH` 指向当前仓库 `src`，以下为集成与收尾命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'answer_geometry_at_supported_sizes or conversation_long_answer or report_recognizes_qvariant or ui_single_submit_codex_response or shell_setup_home_coach_and_settings or answer_hint_hides_on_focus or question_switch_clears_drafts or codex_request_can_stop or setup_requires_consent or coding_actions_stay_visible or interview_completion_copy' -q
# 22 passed, 23 deselected in 110.92s

.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'answer_geometry_at_supported_sizes or conversation_long_answer or shell_setup_home_coach_and_settings or composer_tools' -q
# 最后滚动条定位检查：8 passed，1 failed（展开语音未定位到录音入口）

.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'conversation_long_answer or composer_tools or report_recognizes_qvariant' -q
# 修正语音定位后：5 passed, 41 deselected in 21.68s

.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_desktop.py -k 'interview_setup_uses_profile_role_availability_and_real_report or no_ai_interview_setup_explains_the_ai_boundary' -q
# 2 passed, 36 deselected in 0.41s

git diff --check
# 通过
```

此前只执行本页迭代所需的 Before / 首轮输入 / 长文本 / 布局子集：Before 6 passed；首轮输入 1 passed；长回答首轮 10 passed、2 failed，修复后该子集 3 passed；细滚动条与复盘子集 10 passed；新增工具检查单独 1 passed。这些组相互重叠，**不相加冒充独立测试数**。当前覆盖 23 个不同的界面交互参数化用例及 2 个既有静态契约；最后暴露的失败均有直接修复和复验。

作答布局覆盖 **900×620、1080×680、1280×800、1440×900 × 浅/深色 × 100%/125% 字号**；准备页覆盖四尺寸、浅/深色，并在最小尺寸检查放大字体、表单滚动与主按钮。另检查长回答 Ctrl+Home/End、中文输入法组字、草稿切题、材料授权、一次提交换题、停止/超时保留回答、手撕入口、证据列表滚动。

截图全部来自本轮正式 QML 工作树，保存于 ignored `workspace/maintainer/interview-polish-20260907/`。已亲自查看 Before、首轮与修正后的深浅主题、小窗口长文本、准备页上下半部、等待/超时、语音展开及复盘：

- Before：`before/interview-1280x800-dark-1.0.png`、`before/setup-1280x800-dark.png`。
- After：`final/interview-1280x800-dark-1.0.png`、`final/interview-900x620-light-1.25.png`。
- 其他：`final/setup-1280x800-dark.png`、`final/setup-scrolled-900-light.png`、`final/report-1280-dark.png`、`final/long-answer-900-light.png`、`final/voice-options-900.png`。

### 终局与限制

`UI_POLISH_READY_FOR_USER_UAT`。改动仍是源码版本 `0.4.0a3` 的分支迭代，不是新桌面 Release。没有运行全量 pytest、CI、打包、macOS 实机或真实云请求；此前真实 Codex 的约 125–128 秒网络重连延迟仍未解决，不将视觉迭代描述为性能修复。

用户原有窗口、UAT 目录及未跟踪资料均保留。运行中的旧 Python 窗口不会热更新；处理未提交回答后，按[源码运行](../../docs/desktop-app.md#源码运行)重新启动，并继续使用原数据目录。

## 2026-09-07：一次提交自动接续与真实 Codex 验证（历史）

基线 `d7570dd4fd778a3a999f8425e72fef1a67a0b0e9`；分支 `fix/dynamic-interview-full-flow-20260905`。本轮只处理用户指出的多次确认、发送失败无具体原因及下一问验证，不改变阶段、题库、Grader 或 mastery，不构建、不触发 CI、不跑全量。

### 诊断与改动

- **多次操作是原界面的真实设计问题**：`InterviewPage.qml` 把保存、请求 AI、确认上下文拆成不同入口。现在动态面试只有“提交并继续”，复用现有保存、Codex / Provider 请求和下一问提交链路；不再要求先自评，也不再弹锁定确认。
- **授权按本场范围确认**：开场明确列出岗位、背景、材料及以后主动提交的回答/历史。相同范围后续不重复确认；旧会话补一次许可，材料、背景或接收服务变化后重新确认。只存 QSettings 指纹和所选连接，不保存正文或 Secret。每次发送仍校验材料 SHA / 授权，未确认不锁定、不发送。
- **失败可继续**：保存失败不发送；已经保存的回答不会因网络/格式错误丢失或在重试时被覆写。连接未建立时自动连接并发送；请求中阻止重复点击，保留停止入口。错误显示在面试页，区分格式、保存、授权和连接，带操作编号。普通 API 会保留所选连接，不在进入下一问时跳回列表第一项。
- **真实失败的证据边界**：未修改基线在 Windows 正式界面上完成了 `q-001 → q-002`，用时 **125.83 秒**，复现了繁琐操作和明显延迟，但没有复现用户那一次相同的通用错误。原来的解码/上下文失败分支确实会经 `friendly_error` 隐藏具体原因；不能据此断言用户那次错误一定是某个字段缺失。针对性试验注入缺少字段的返回，验证现在显示 `AI_RESPONSE_INVALID`，并能用原回答重试。
- **Codex 返回约束**：实际 `turn/start` 使用官方 `outputSchema`，只允许本轮阶段、岗位技能、本地代码候选；本地校验和原子提交仍保留。普通 API 未强行增加不兼容参数。官方接口参考：[Codex App Server](https://developers.openai.com/codex/app-server/)。
- **慢请求不是已修好的性能项**：本机 Codex RPC 初始化/创建 Thread/启动 Turn 通常不足 0.5 秒；模型响应之前多次 `responseStreamDisconnected`、`request timed out`、`Reconnecting 2/5…5/5`，之后才成功。没有修改用户 Codex 配置、代理或认证。曾在隔离进程验证关闭 websocket 的配置候选，但 CLI 拒绝覆盖内置 `openai` provider，该参数未进入产品代码。

### 实际测试与证据

使用当前仓库 `src`、真实 Windows `Main.qml` / `AppController`，新建合成档案 `profile-ef2c6a37`、合成简历和 JD；岗位后训练、实习、高压，真实 Codex **gpt-5.6-sol / low**。不是 DemoController，不预置未来题目，不读取真实用户 Profile / 简历。键入和点击由 Qt Windows 事件驱动；后续回答针对实时返回的问题输入，不注入 AI 响应。

定向命令均先设置 `PYTHONPATH=<当前仓库>/src`、`QT_QPA_PLATFORM=windows`：

```powershell
# 第一组：一次提交、重试、旧会话授权、连接与输入
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'single_submit or answer_hint_hides' -q
# 6 passed, 32 deselected in 27.27s（当时版本；后补充的用例在下一组验证）

# 集成组：新增提交用例、四尺寸、上下文、停止及多轮去重
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'single_submit or answer_geometry or codex_request_can_stop or context_dialog_long_labels or dynamic_followups_advance_once' -q
# 18 passed, 23 deselected in 77.88s

# 仅补验最后改动的前置错误分支
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'send_preconditions' -q
# 1 passed, 41 deselected in 7.08s

# 既有固定评分兼容与界面绑定契约
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_desktop.py -k 'interview_setup_uses_profile_role_availability_and_real_report or provider_assessment_scores_the_locked_answer_once' -q
# 2 passed, 36 deselected in 5.76s
```

以上分组有重叠，不相加冒充独立测试数量；没有运行 `pytest -q` 全量。18 项集成检查覆盖 900×620、1080×680、1280×800、1440×900，浅/深色与 100% / 125% 字号。已亲自查看小窗口浅色放大输入/提交、真实 Codex 等待及第三问截图；文字、提示和主按钮未重叠，长内容通过滚动阅读。

隔离证据位于 ignored `workspace/maintainer/interview-submit-20260907/`：`before-repro.log`、`after-live-4.log`、`after-live-5-coding.log`、`restart.log`、`live.py`、`restart.py`、`after-q-*-*.png`、`ui-final/`。运行命令为 `.\.venv\Scripts\python.exe workspace/maintainer/interview-submit-20260907/live.py`；初始探针曾因组合框/滚动/勾选事件操作错误退出，修正的是私有探针，不把这些当成产品成功。第六题时探针引用了旧按钮名 `startInterviewCodingAnswer`，修为现有 `toggleInterviewCodingPrompt` 后重新启动同一目录，从已保存第六题继续，没有重建 Session 或重复五次模型请求。这不是一次无中断的机器人脚本成功；下面结果来自实际持久化的同一场面试。

真实结果：

| 问题 | 实际内容 / 结果 | 提交到下一问 |
|---|---|---:|
| q-001 | 本地自我介绍；明确竞赛数据清洗、DPO 对照与个人贡献 | 124.67 秒 |
| q-002 | Codex 根据回答询问 chosen/rejected 长度捷径、切分与可核对结果 | 126.53 秒 |
| q-003 | 根据上一轮继续追问长度定义、分组连通性、实际记录与重建设想的区别 | 127.88 秒 |
| q-004 | 自动进入 DPO 损失、reference、beta 与长度偏差的岗位原理 | 127.98 秒 |
| q-005 | 针对上轮 beta 解释的缺口，追问 KL 方向、饱和及诊断量 | 125.31 秒 |
| q-006 | 从本地有效候选选择 FND-002，打开真实编辑器并运行 Grader | 0 通过 / 10 失败 |

五个口述回答均通过真实按钮单次提交，没有锁定弹窗或每轮上下文弹窗；没有提前写入未来题目。代码测试刻意使用未实现 starter，revision `06df2e7b…`，记录 0 分而非伪造 PASS；它是当前本地可运行的基础 Python 题，不冒充新生成的高阶 DPO 手撕题。结束后 `status=completed`、`flow_coverage.complete=true`、六条评分证据，其中五条真实 AI、一条真实 Grader；没有缺失阶段，也没有修改 Practice mastery。**完成流程不等于面试通过。**

再次运行 `.\.venv\Scripts\python.exe workspace/maintainer/interview-submit-20260907/restart.py`，输出 `RESTART_OK profile-ef2c6a37 completed 6 6 consent retained`。确认恢复同一档案、六题、六条证据、报告、材料范围、所选连接、模型和推理强度；解释器加载的是当前仓库的 `desktop/controller.py`。

已实际查看 `after-q-001-sending.png`、`after-q-003-question.png`、`after-final-report.png` 和 `after-restart-light.png`，以及 `ui-final/interview-900x620-light-1.25-submit.png`。真实服务截图使用合成候选人，Fake 模型布局截图仅证明布局，不混淆为真实服务验证。没有替换 README 的 Release 截图。

### 收尾状态

`REAL_CODEX_SINGLE_SUBMIT_FLOW_COMPLETED / WAITING_FOR_USER_UAT`。

- 真实 Codex 整场和重启验证已完成；**125–128 秒的网络重连延迟仍未解决**。目前下一问在完整 JSON 校验后显示，不是逐 token 渲染问题。
- 普通云 API 本轮只有 Fake Provider 的传参/回调验证，没有真实 Key 调用；没有 macOS 实机、完整回归、CI、打包或 Release。
- 用户原有窗口和未跟踪 UAT/反馈全部保留，避免关闭尚未保存的回答。已运行的旧窗口不会热更新 Python；保存/处理原回答并关闭后，按[源码运行](../../docs/desktop-app.md#源码运行)重启，继续使用原数据目录，不要重置档案。

## 2026-09-07：操作体验迭代与源码验收（历史）

基线 `ef336e448ef1f5eb7228bd446ea7c42580fb853f`，分支 `fix/dynamic-interview-full-flow-20260905`。本轮不改变动态面试流程与评分规则，不构建应用，不触发 CI，不运行全量测试。

### 已复现并处理

1. **手撕入口藏在长题面底部**：Windows 正式窗口在 900×620、1280×800 的原始截图中，首屏找不到运行按钮。现在保留原题文字，题面/代码按需切换，底部固定保存、保存并测试、记录动作；只保留一个主强调按钮，去掉重复题目标题。
2. **测试状态容易误读**：原来的 `coding_test_current` 表示“这个版本已经测过”，不表示 PASS，但 UI 一律使用绿色。现在明确显示通过/未通过及 revision；输出绑定本题，不读取刷题页的全局输出。按钮与 Ctrl+R 调用同一方法，测试最新编辑器文本，修改后阻止使用旧结果记录本轮。
3. **连接编辑定位与层级**：点击列表中的编辑后自动回到配置表单并选中模型；保存主按钮使用统一样式。连接卡片按内容增高；只有结构化 `ready=true` 才显示绿色，未测试不再通过文案猜测为可用。
4. **未提交面试回答时仍能切换档案**：用两个新建合成档案复现，两个档案拥有相同 Session/Question ID。现有切档入口补上未提交回答/未保存代码门控，页面身份包含 Profile ID；提交后切换，新档案不带入旧文本，切回仍能读到已锁定原回答。
5. **结束状态反逻辑**：答完最后一题但尚未结束时显示“本场作答已完成 / 结束并查看复盘”；结束后显示真实复盘，不再出现开场指引和无效的结束按钮。移除“动态模式尚未衔接代码题”的过期说明。

### 实际验证

使用正式 `Main.qml`、真实 `AppController`、真实 Session 持久化和 Windows Qt 输入；QSettings 重定向到测试自己的 INI，没有操作真实学习档案或系统 Keyring。用于进入后续环节的模型回复是**明确标记的合成 fixture**，本轮没有再次调用真实 Codex/云 API，不将本轮 UI 测试算作新的一场真实 AI 实测。

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) "src"
$env:QT_QPA_PLATFORM = "windows"
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'coding_actions_stay_visible or edit_saved_connection_reveals or saved_connection_card or coding_runs_visible_revision or completion_copy or profile_switch_preserves_unsent or answer_hint_hides or question_switch_clears or answer_geometry or report_recognizes or reconfigure_preserve' -q
# 18 passed, 17 deselected in 86.91s

.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py -k 'coding_runs_visible_revision and button' -q
# 1 passed, 34 deselected in 9.80s
```

第二个命令仅补验“记录真实失败的手撕结果 → 结束确认 → 生成完整流程报告”，没有重复整个领域。手撕使用未实现 starter，真实 Grader 结果为 failed；“完成流程”不等于代码通过或 mastered。

开发前的定向复现：初版测试探针因预览 hash 字段与布局等待写错而失败，修正探针后得到 `2 failed, 1 passed`（两种窗口运行按钮均在视口外）；初次修改后 8 项通过。切档问题另有 `1 failed → 1 passed`，最后统一纳入上述 18 项验证。

布局检查覆盖 900×620、1080×680、1280×800、1440×900；手撕分别检查浅色 100% 和深色 125% 字号，既有回答框测试也检查两主题的 100% / 125%。实际查看了小窗口手撕、失败输出、连接编辑、连接列表和复盘截图。完整题面、长代码和测试输出通过滚动阅读，不声称在小窗口一次显示全部内容。

截图保存在 ignored `workspace/maintainer/ux-20260907/before/` 和 `after/`，不是 Phase 0 原型。代表文件：`coding-editor-900-light.png`、`coding-editor-900-dark.png`、`coding-failed-shortcut.png`、`connection-edit-small.png`、`connection-saved-small.png`、`interview-ready-to-finish.png`、`interview-completed-report.png`。报告截图分数来自合成口述评分与真实失败代码测试，仅用于验收 UI，不代表真实候选人水平。

另外使用正常入口 `pythonw.exe -m llm_interview_lab.desktop.main` 启动了一个可交互 Windows 窗口，没有 `--smoke-test`、截图参数、预置档案或 DemoController。验收目录为 `workspace/maintainer/manual-uat/`，窗口标题为 `LLM Interview Lab`，窗口句柄有效且进程可响应。首次准备该目录的启动日志记录首窗口 **8341 ms**；这是一台设备的一次样本，不是所有启动的性能承诺。日志位于本轮 ignored 证据目录 `source-bootstrap.log`。

已用解释器确认实际加载当前仓库 `src/llm_interview_lab/desktop/main.py`，`--version` 为 `0.4.0a3`。源码启动和保留验收数据的方法见 [桌面指南](../../docs/desktop-app.md#源码运行)。`git diff --check` 通过。

### 未验证和剩余限制

- 本轮没有真实云 API、Codex 重新联网测试、macOS 实机、全量 pytest、CI 或打包；上一轮真实 Codex 证据见下一节，不能外推为本轮全平台验证。
- 上一轮 Codex 请求约 125–136 秒的延迟，本轮未解决；网络/模型兼容性仍需用户使用实际连接验收。
- 尚未提交的口述草稿仍仅在当前窗口内；关闭前应提交并锁定，代码应保存。此次修复针对切档保护，不宣称实现崩溃草稿恢复。
- 手撕保持本地冻结原题，部分题面仍为英文；不把本轮布局调整称为完整中文版 Coding Workbench。

终局：`READY_FOR_SOURCE_UAT`。既有未跟踪文件和旧 UAT 目录保留，不入提交。

## 2026-09-06：真实 Codex 整场面试与修复结果

本节覆盖本次实际执行；下方旧记录保留，不代表当前仍只有首题。**本次完成了一场真实 Codex + Windows 正式 QML 的六题面试，并重启恢复报告。** 不是 DemoController，不是用 Fake 返回冒充真实模型，也没有发布新的桌面包。

### 基线与修改范围

- 起始 SHA：`972e85c6b06a83114f0b49cb2c8fc20426e4fc82`。
- 分支：`fix/dynamic-interview-full-flow-20260905`。
- 实现提交：`ec46bba32a475b6ca4217903bc3ef7d44445459a`，11 个源码、Schema、目标测试文件。
- 原有未跟踪反馈、产品计划、原始图标与 `.uat-*` 目录全部保留；没有提交真实档案、材料、Secret 或本次手撕实现。

解决的实际缺口：

1. 每轮补齐完整岗位技能说明、难度、求职背景和本场历史问答；普通 API 不再只能看到孤立的当前回答。
2. 新增薄的流程约束：自我介绍 → 经历深挖及追问 → 岗位原理及追问 → 本地手撕。经历与八股各 2–4 问；模型根据实际回答决定问题及何时进入下一阶段，不生成未来题单。
3. 一个 Application Use Case 校验并原子提交本轮评分和下一问；无效阶段、技能或代码题 ID 不会留下“已评分但无法继续”的半成品。
4. 正式面试设置可以同时选简历与 JD / 补充材料；逐场许可、每次上下文确认及 SHA 校验继续生效。
5. Codex 每次使用新的传输 Thread，显式带入本场已发生的历史。不是丢掉上下文，而是不让其他场次或本轮取消授权的材料从旧 Thread 隐式进入请求。
6. 动态面试完整性与评分按阶段计算；只有问答、追问与本地代码证据均完成才标记 `completed`，缺代码时不伪装完整。
7. 真实点击发现模型保存会触发 QML 重绑定，抹掉尚未保存的推理强度；现先捕获两项输入再保存。
8. 真实报告截图发现有六条评分证据却显示“尚未评分”；原因是 `Array.isArray` 不识别 Python 传入的 QML sequence。已按 Schema 的列表直接读取，修复后显示分数及 AI / 本地 Grader 来源。

### 真实试验：不是预置 AI 回复

运行目录：`workspace/maintainer/dynamic-full-20260905/`（Git ignored）。

- 通过正常 `desktop.main.main()` 启动 Windows 窗口，Qt Test 实际点击、输入、滚动、锁定、确认发送、运行测试和结束；没有使用演示控制器。
- 新档案通过真实 Onboarding 创建：`profile-c88b4397`。所有简历、JD、回答均为明确标注的合成案例，不对应用户本人。
- `resume.txt` / `jd.txt` 通过正式材料接口导入并授权；未读取用户真实 PDF、DOCX、历史 UAT 档案或系统 Keyring。
- 岗位为后训练、求职阶段为实习、难度为高压。背景是偏好数据清洗、DPO 对照与合成比赛经历，明确没有真实论文和企业实习；模型没有编造这些经历。
- 实际 `model/list` 确认可用模型后，在正式设置页保存 `gpt-5.6-sol` / `low`；五次 `turn/start` 实际传参均为该模型和强度。

| 已发生的问题 | 来源与真实内容 | 结果 |
|---|---|---|
| q-001 自我介绍 | 本地通用开场；回答说明合成比赛、个人贡献、结果缺口 | Codex 评估后生成 q-002 |
| q-002 经历深挖 | Codex 根据简历和首轮回答问用户/语义图划分、巨大连通分量与泄漏统计 | 锁定回答后继续 |
| q-003 经历追问 | Codex 针对刚回答的“低信息桥接边”追问处置规则、统计证据 | 明确区分实际证据与假设方案 |
| q-004 岗位八股 | Codex 根据后训练技能与上下文询问 DPO 目标、beta、长度捷径 | 锁定回答后继续 |
| q-005 八股追问 | Codex 追问 beta 的方向、初始化梯度、饱和和控制变量消融 | AI 选择下一环节的本地题目 |
| q-006 手撕 | 模型选择已验证 `FND-002`，本地冻结原题与接口；正式编辑器输入代码 | 真实公开测试 `10 passed in 0.08s`；Grader 记录耗时 633 ms |

本场只按发生顺序写入 6 道题和 6 条评估，没有提前写入未来问题。首题是本地开场，不宣称它来自 Codex；后续四条口述问题是实时生成，代码题是 AI 从本地候选中选择，**不是临时生成未验证的代码题**。

最终 `role-interview-0001`：`status=completed`，`flow_coverage.complete=true`，没有缺失阶段，AI 证据与 Grader 证据分别记录；样例总分 84.8 只属于这份合成回答，不是用户能力、Offer 概率或 mastery。

五次实际等待：127.05 / 125.09 / 136.19 / 129.73 / 126.17 秒。当前模型与线路仍然很慢；没有凭猜测归因，也没有声称延迟已解决。面试开始于 `2026-09-05T16:19:08Z`，结束于 `16:36:46Z`，期间包括测试者阅读、输入和截图。请求仍可停止，180 秒超时后保留回答。

### 重启与截图复核

新进程正常加载同一档案、同一已完成 Session、6 道问题和 6 条评分证据；模型及 `low` 偏好保留。读取报告不需要重新连接 AI。

实际打开检查了作答、上下文、手撕结果及深浅主题报告截图。以下文件都在上述 ignored 运行目录，不进入公开题库或 Release：

| 文件 | 用途 / SHA-256 |
|---|---|
| `q-001-typed.png` | 正式中文输入，提示已隐藏、文字位于输入框内 |
| `q-003-question.png` | 真实针对上一回答的追问；`7da6aada13847eac582f4fad012130ec9899e61df405bb0a990c244722bf88c9` |
| `q-004-context.png` | 本轮上下文确认，列表可滚动、按钮独立 |
| `q-006-grader.png` | 真实编辑器及可记录的代码证据；`2aca2f58af18ef3f830524c1326cb495bb182e1602b681558171d3cf85c540ab` |
| `report-restarted-dark.png` | 重启后报告与评分来源；`c1519380e8056b94524e9b318d666465015f10c3ba12e331024387f249069a91` |
| `report-restarted-light.png` | 浅色报告；`449e460fe9aa1d524efb6bb7f29d7d26a99753f2b3dd629c2d4fe16a8d633830` |

测试隔离也发现并修正一处问题：Windows 的 `QSettings(organization, application)` 不使用 `setDefaultFormat(IniFormat)` 设置的目录。早期测试写到了非敏感的全局模型偏好，使重启读到测试占位值 `selected-model`；不是产品保存不落盘。目标测试已改为显式私有 INI 构造器，本次运行也将仅属于合成档案的指针与已知模型偏好复制到其私有 INI，并复验恢复。占位模型已改回本次真实选择的 `gpt-5.6-sol / low`，主题恢复为深色；没有读取或改写真实档案/材料/Key。不能把初次设置隔离失败隐去，也不声称恢复了测试前未知的模型偏好。

### 实际测试命令与结果

使用当前仓库 `src` 的 `PYTHONPATH`，`.venv/Scripts/python.exe`，`PYTHONNOUSERSITE=1`、`PYTHONUTF8=1`；Qt 目标测试为 Windows 平台。以下缩写 `F` 为 `tests/infrastructure/test_dynamic_interview_flow.py`，`I` 为 `tests/infrastructure/test_interview_input_runtime.py`。

- `pytest F -q`：首轮 1 passed / 4 errors，测试材料类型误写为 `jd`；改用现有 `job_description`，对应四例重跑通过。不是新增材料类型。
- `pytest I -k "ui_lock_preview or followups" -q`：4 passed；随后加入每轮确认与隔离 Thread 后，连同 `api_wire` 合计 7 passed。
- 模型保存与 Stop/Timeout：先发现旧 fixture 未调用新的上下文确认；补齐确认和 Fake `start_thread` 后 Stop/Timeout 2 passed。没有放松生产确认条件来使测试通过。
- `pytest I -k setup_requires_consent -q`：1 passed；简历+JD 未许可不能启动，许可后真实创建仅含首题的 Session。
- 模型保存与报告：模型保存用例通过；报告断言由 Python `5.0` 调整为 QML 实际显示 `5` 后通过，不改评分值。
- 真实 Windows 命令：`.venv/Scripts/python.exe workspace/maintainer/dynamic-full-20260905/live.py`；初次脚本有滚动/点击定位问题，修正测试驱动后实际完成上述六题。等待文件只用于人工逐题提供合成回答，不预置任何 AI 回复。
- 重启命令：`.venv/Scripts/python.exe workspace/maintainer/dynamic-full-20260905/restart.py`；在修正测试设置隔离及报告派生字段的比较方式后，输出 `RESTART_OK profile-c88b4397 completed 6 6`。

最终代码收敛后的唯一组合验证：

```text
.venv/Scripts/python.exe -m pytest tests/infrastructure/test_dynamic_interview_flow.py tests/infrastructure/test_interview_input_runtime.py -k "context_keeps or revoked_material or invalid_ai_stage or full_flow or stage_bounds or api_wire or settings_saves_model or setup_requires_consent or report_recognizes or codex_request_can_stop or ui_lock_preview or dynamic_followups or answer_hint_hides or answer_geometry or context_dialog_long" -q
24 passed, 9 deselected in 71.74s
```

覆盖真实核心流程、材料权限、逐轮历史、非法结果不半提交、模型/强度、Stop/Timeout、中文 IME、上下文弹窗与 900×620 / 1080×680 / 1280×800 / 1440×900 的目标布局（深浅、100%/125% 字号）。`git diff --check` 通过。

### 能力边界与未验证项

- **真实云端已验证：** Codex 的 `gpt-5.6-sol / low`，本场后训练实习高压场景。其他 Codex 模型可配置，但没有逐个进行同等实测。
- **普通 API：** OpenAI、OpenAI-compatible、Ollama 的现有 HTTP/SSE 适配器通过 MockTransport 验证模型、推理参数和完整上下文；Controller 的 Provider 后续问题通路通过 Fake 结果验证。没有可供本次独立使用的 API Key，也没有读取用户 Keyring，因此不声称真实普通云 API 已端到端验证。
- 本次合成材料是 UTF-8 文本，未复测 PDF/DOCX 提取、扫描 PDF/OCR、真实用户材料、录音或 STT。
- 代码候选由现有题库和求职阶段限定；本次选中的 `FND-002` 是基础数据校验，不代表已验证高难 DPO/PPO 手撕质量。题面保留冻结英文原题，尚未统一成中文。
- 本次不是所有岗位、所有简历类型的面试效度评估；没有新增岗位或题库，没有修改 mastery。
- 未运行完整 pytest、完整 CLI/课程回归、CI、Windows/macOS 打包、macOS 实机或 Release 验收。代码已修复不代表已发布桌面包自动更新。

裁决：`REAL_CODEX_INTERVIEW_COMPLETED / TARGETED_24_PASSED / WAITING_FOR_USER_UAT`。

---

## 2026-09-05 再次迭代：ChatGPT 风格与实际排版验证

本节是最新 UI 结果；下节保留此前的真实 Codex 传输记录。此次不修改面试状态机、材料权限、Provider 或掌握规则，不把 UI 更新描述为完整动态面试引擎完成。

### 基线与源码

- 分支：`fix/desktop-input-interview-20260905`；本轮起点 `04f87c7f7bbef1c125cc2ad0e1a2c45839fd91c8`。
- `2e9b083`：中性色、扁平导航、面试单列视图、底部主动作、内容自适应布局和目标测试。
- `2a6cca1`：消除确认弹窗继承 Material 底栏造成的贴边；增加按钮底部留白检查。
- `ff6ebaa`：最终浅色截图发现 Coach 两处旧按钮白字浅底，改用既有中性按钮，并补充入口颜色检查。
- 版本仍为 `0.4.0a3`，没有更新 main、Tag 或桌面发布包。两个 deploy spec 仅补齐新 QML 文件清单，没有执行构建。

### 实际改善与发现

1. **视觉收敛**：参考 ChatGPT 的中性色与内容优先原则，将紫色主按钮改为深浅反差的中性主按钮，蓝色用于焦点和链接；设置、作答不再并排占用两个大框。使用 OpenAI Docs 技能核对了 [官方 UI 指南](https://developers.openai.com/plugins/concepts/ui-guidelines)；该页面面向 ChatGPT 插件，借鉴的是原则，不宣称完整复刻官方桌面规范。
2. **输入区**：保留上一轮 Basic 输入控件的获焦/IME 提示隐藏逻辑；本轮统一输入内边距，删除 Coach 额外叠加的提示层。实际发送中文组字事件和提交文本，检查提示不可见、光标位于输入区内。
3. **题面行高**：运行中发现 Markdown 文本实际 `contentHeight=64`，控件高度却只有 `52`；现在题面按实际内容高度布局，标题、题面和回答框不交叠。
4. **首页越界**：900×620、125% 字号下，“继续面试”的文字底部位于卡片内 `y=229`，卡片高度只有 `226`，截图可见按钮越界。首页主要任务卡现在由内容撑高；学习证据仍按内容高度布局，短窗口通过页面滚动查看下方内容。
5. **主按钮可达**：初版迭代中，锁定回答后的“让 Codex 继续提问”仍在滚动区域边缘，真实点击测试失败。已将这组现有动作和请求状态移到底部，与回答前的提交动作统一留在可操作区域；没有复制请求方法。
6. **确认弹窗**：上下文标签、材料说明和摘要不再使用固定行高；两处弹窗共用一个内容高度驱动的列表，长材料可滚动。最后截图检查还发现 Material 底栏导致按钮贴边，统一为 Basic 后，按钮距弹窗底部至少 12px 的检查通过。
7. **层级与可读性**：岗位、难度与状态收纳到“本场信息”；结束后可以查看原结果或“再面试一场”。导航在合适宽度显示文字，档案区域不使用固定 70px 高度。文字、主要按钮、输入边界、焦点环的既有对比度要求保留并通过。
8. **浅色入口**：最后逐图查看时发现 AI 辅助页的新建入口仍继承旧高亮样式，白字落在浅色背景上。改用相同的 LabButton 后，文字和按钮可见；没有把这张有缺陷的图片作为最终证据提交。

### 验证方法与实际命令

`I` = `tests/infrastructure/test_interview_input_runtime.py`；`D` = `tests/infrastructure/test_desktop.py`；`S` = `tests/infrastructure/test_desktop_design_system.py`；`O` = `tests/infrastructure/test_onboarding_qml_hotfix.py`。下表均使用 `.venv\Scripts\python.exe -m pytest`，参数中的别名表示相应完整路径。

真实窗口组使用 `PYTHONPATH=src`、`PYTHONNOUSERSITE=1`、`PYTHONUTF8=1`、`QT_QPA_PLATFORM=windows`、`QT_QUICK_BACKEND=software`、`QT_QUICK_CONTROLS_STYLE=Material`；证据输出到 ignored 的 `workspace/maintainer/chatgpt-ui-20260905/`。不是 offscreen 截图，不调用真实账户，不读取已有 UAT 档案。

| 实际参数 | 结果 / 修订原因 |
|---|---|
| `I -k answer_geometry_at_supported_sizes -q` | 初次 4 errors：NavItem 的 contentItem 同时使用对象与分组赋值；修正后 QML 编译通过 |
| `I -k "answer_geometry_at_supported_sizes and size0" -q` | 1 passed；首次小窗口检查 |
| `I -k "answer_geometry_at_supported_sizes or context_dialog_long_labels or session_details_and_reconfigure or ui_lock_preview_codex_response" -q` | 4 failed / 4 passed；定位题面实际行高超出控件高度 |
| `I -k answer_geometry_at_supported_sizes -q` | 修正后 4 passed；四种尺寸，每种含深浅主题 × 100%/125% 字号 |
| `I D -k "shell_setup_home_coach_and_settings or answer_hint_hides or long_toast_grows or interview_setup_uses_profile_role_availability or no_ai_interview_setup_explains" -q` | 7 passed |
| `I -k small_home_and_coach -q` | 初次 2 failed；实测首页按钮越出固定高度卡片 |
| `I -k "small_home_and_coach or context_dialog_long_labels or (answer_geometry_at_supported_sizes and size2)" -q` | 高度修正后 5 passed；同时检查长材料末行可滚动到达 |
| `S -k "theme_pairs or semantic_and_legacy or shell_breakpoints or shell_and_legacy_home or exactly_cover" -q` | 11 passed / 1 failed；断点测试仍匹配旧表达式，随后按实际新断点更新 |
| `S I O -k "shell_breakpoints or (answer_geometry_at_supported_sizes and size2) or ui_lock_preview_codex_response or role_picker_and_primary_action_remain_visible" -q` | 6 passed / 1 failed；实际点击发现锁定回答后的继续按钮被滚动区域裁切 |
| `I -k ui_lock_preview_codex_response -q` | 底部操作区修正后 2 passed；900×620 与 1280×800，均为 125% 字号 |
| `I -k "(answer_geometry_at_supported_sizes and size2) or (ui_lock_preview_codex_response and size1) or (small_home_and_coach and light)" -q` | 3 passed；代码收敛后保存正式页面证据 |
| `I -k "context_dialog_long_labels or (ui_lock_preview_codex_response and size1)" -q` | Basic 底栏修订后 3 passed；上下文内容、底部留白和实际确认发送 |
| `I -k small_home_and_coach -q` | 浅色入口修正后 2 passed；重新保存深浅主题的小窗口截图 |

共 **34 个不同的定向用例最终通过**：正式 Controller 的窗口交互 16 个、Desktop 静态契约 2 个、主题/对比度/资源清单 12 个、既有岗位列表几何检查 4 个。最后一组岗位列表使用已有测试 fixture，只证明布局，不替代真实建档验收。没有将分组测试说成完整 pytest 通过。

真实交互路径：输入合成中文回答 → 点击提交 → 确认锁定 → 点击继续提问 → 查看上下文 → 确认发送 → **Fake Codex** 返回 → 正式 Controller 保存并显示 `q-002`。本轮不增加真实 Codex 账号或网络性能验证结论。

### 截图与边界

- [深色面试](../../docs/images/chatgpt-ui-20260905/interview-dark.png)、[浅色面试](../../docs/images/chatgpt-ui-20260905/interview-light.png)：1280×800、100% 字号。
- [上下文弹窗](../../docs/images/chatgpt-ui-20260905/context-dark.png)：1280×800、125% 字号；连接状态来自明确的 Fake Codex 测试。
- [小窗口首页](../../docs/images/chatgpt-ui-20260905/home-small-light.png)、[小窗口 AI 输入](../../docs/images/chatgpt-ui-20260905/coach-small-light.png)：900×620、125% 字号。
- [截图清单](../../docs/images/chatgpt-ui-20260905/manifest.json)逐图记录源码 Commit、时间和 SHA-256；这些是隔离合成数据的正式页面，不是 Phase 0 原型，也不是新发布包。上述图片均实际查看；另查看了设置、长材料和提交后状态的本地截图。
- 文档收尾检查：5 张图片的 SHA-256 / 大小与清单一致，两个修改文档中的 16 个相对链接存在；`git diff --check` 通过。
- 本轮没有运行完整 pytest、RC CI、Windows/macOS 打包、真实 API/Codex 网络调用或 macOS 实机验收。没有宣称所有页面与所有系统绝无排版问题。
- 既有未跟踪反馈、原始图标、计划和 UAT 数据全部保留；只提交本轮源码、目标测试和经检查的合成截图。README 的发布截图不替换为尚未发布的分支界面。
- 动态面试完整上下文连续性、阶段推进、自动 Coding 衔接和网络重试时延仍是上一轮列出的限制，不因这次外观更新而视为解决。

状态：`UI_TARGETED_VERIFICATION_PASSED / WAITING_FOR_USER_UAT`。

---

## 2026-09-05 补充：正常启动入口与真实 Codex 交互

本节保留上一轮的真实传输结果。下节“版本核对与输入 / 追问修复”记录的是更早的 Fake 验证；本节增加实际 App Server 传输证据，不把它扩大成完整动态面试或 Release 验收。

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
