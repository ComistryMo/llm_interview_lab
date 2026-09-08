# 动态面试：多角度深挖与自由手撕

基线：`dbc9aba`，开发分支 `fix/dynamic-interview-full-flow-20260905`。

## 目标与当前事实

用户要求：项目不能只追一个方向；经历后需要 3–4 道相关八股；困难体现提问深度和广度，不是评分宽容度；手撕可运行自己写的 Python 样例，未完成代码也能交面试官评逻辑。

改动前的基线 `interview_flow.next_stages` 将经历和原理各限制为 2–4 轮；策略文件仅建议概述后一到两轮深入。`role_interviews` 的代码评分只接受 Grader 通过=5/失败=1，Controller 也拒绝 AI 评 coding。这些是本次明确改变的产品语义，不是增加更多固定题。

## 范围与实施切片

1. 调整逐轮过程与实际发送的岗位/难度策略：项目至少展开多个角度，允许深入多轮；原理至少三问、建议 3–4 个知识主题，按剩余时间而不是四轮上限安排追问。上下文明确已问内容、阶段进度、剩余时间及阶段转场要求。旧报告不重写。
2. 在现有面试编辑器增加保存并运行当前 Python 脚本（含可选标准输入、输出/错误/超时），不要求固定入口或通过单测；正式单测仍单独保留。提交给 AI 时冻结代码和本次运行事实，逻辑评价与客观执行结果分开，AI 不得把未运行或失败改成测试通过。复用现有 Codex/API 传输与评分流程。
3. 定向验证与真实 QML 操作，更新用户文档，提交推送当前开发分支；不合 main、不构建、不跑全量/RC。

不修改 Practice、Catalog、固定题接口、Mastery 或 Grader 成败含义；不访问真实 Profile/材料/Key，不重写界面框架。用户主动运行的是其信任的本地 Python，不宣称沙箱。

## 验收与风险

- 困难经历可超过四问；每次仍仅生成下一问，提示要求转换到其他有证据的角度，不预生成整场题单。
- 正常完成不能跳过三问原理；提前结束或时间不足明确保留缺失环节，不能伪装完整。
- stdout/stdin、语法错误、超时、中文路径和代码 revision 可验证；自测不是单测通过证据。
- 未运行/未完整实现的代码可获有依据的 AI 主观分；旧 Grader 分仍保持独立且绑定原 revision。
- 重试不篡改已锁定代码，切题/切档旧异步结果不覆盖当前题。
- 只运行相关 flow、coding、context 和 QML 测试。模型是否能稳定问得深入属于内容质量验证，不用合成回复冒充真实模型表现。

## 决策与进度

- 复用现有答案快照和评分来源，优先不增加第二套 Session 或运行框架。
- 阶段数量约束保证不漏环节；语义上的深度/主题相关性由实际 prompt、完整已发生对话和质量检验共同约束，不声称确定性代码能证明自然语言质量。
- 当前状态：`READY_FOR_MANUAL_INTERVIEW_UAT`。`ef3bc72` 中的最后两处修复已完成直接复测；以下关机检查点保留为历史事实，最新结果见末尾。

## 2026-09-08 关机检查点

状态：`CHECKPOINT_SAVED_PENDING_TARGETED_RETEST`。本检查点不是最终验收通过，不创建 Release 或合并 main。

已实施：实际发送的项目多角度/八股/难度策略；移除四轮与旧追加路径二十问上限；Python 自由执行、可选 stdin、输出/错误/超时；代码与执行事实按 revision 锁定；Codex/API 主观代码评分与 Grader 事实分离；正式页面操作与报告文案。

此前目标验证：

- `test_dynamic_interview_flow.py`：16 passed / 126.08 秒。
- 同文件新增 self_written、failed_script、difficulty_changes：5 passed / 37.85 秒。
- 正式 QML 的 coding_actions_stay_visible、real_coding_ui、interview_coding_runs_visible_revision：7 passed / 151.54 秒，覆盖四种窗口尺寸、浅深色及放大字号；UI 的 AI 返回值使用测试替身。
- `test_role_interviews.py` 的 coding_assessment_is_grader_bound、finish_rejects_answer_file_changed、grader_source_is_restricted：3 passed / 15.46 秒。

独立复核（functional_acceptance，未参与当前实现）发现旧 PASS 界面误导与 stdout 采集内存无界两点，随后源码复核 Approved：保存/公开测试/脚本执行共用当前 revision 更新；输出改用临时文件，轮询 64 KB 预算与超时，输入也用临时文件避免管道阻塞。

**最后一次复测并非通过**：选择 real_coding_ui 和 self_written，共 3 failed / 2 teardown errors。直接原因是新增自动滚动把 QML 点坐标写成 `.y()`，以及临时文件读取保留了 Windows CRLF 导致输出断言失败。两处已分别改为 `.y` 和统一 `\r\n` → `\n`。用户要求关机，未启动下一轮测试，不用之前的 31 项通过证明这两处最终修复已经通过。

真实 Codex 合成内容抽查：使用本机列出的 `gpt-5.6-sol`、`medium`，三个响应均通过应用 JSON 解码。已确认 CoT 讲清后转向 GRPO 组内优势和策略梯度；已问三个理论主题后转向验证器投机及对照实验；未完成 MHA 得到核心逻辑 3 / 解释 3 / 验证 1，明确未运行与缺少 causal mask/合头/返回值，没有虚构 PASS。仅为三个合成上下文探针，不是整场真人面试或所有模型保证。每次约 125–127 秒，真实延迟仍是限制。本机默认模型首次探针因 Codex 版本不兼容失败；没有修改用户模型设置、凭证或升级 CLI。

原始合成探针和正式页面截图位于 ignored `workspace/maintainer/agent-runs/interview-depth-20260908/`，不含真实 Profile 或材料。没有读取真实简历/Key，没有关闭用户原有应用。此前测试与探针均已退出，不留后台验证任务。

### 下次最短继续方式

先只复测本次失败的三个用例：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:QT_QPA_PLATFORM = 'windows'
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interview_input_runtime.py tests/infrastructure/test_dynamic_interview_flow.py -k 'real_coding_ui or self_written' -q
```

若通过，再看自动滚到运行输出的正式页面截图与“旧公开 PASS → 新脚本执行”的过期标识；随后交用户人工验收。不需重跑全量，不重复调用真实模型或打包。旧已冻结 Rubric/历史报告不重写，新策略完整体验应新开一场；语义主题是否足够不同仍需真实面试 UAT。

## 2026-09-08 继续执行与收尾

实际检出的分支为 `fix/dynamic-interview-full-flow-20260905`，复测源码为 `ef3bc72`；本轮没有额外修改生产代码。已有未跟踪材料、UAT 目录和反馈文件全部保留，不加入提交。

执行上文三个定向用例，增加 `LLM_LAB_UI_EVIDENCE_DIR` 指向隔离证据目录，结果：

```text
3 passed, 106 deselected in 69.90s
```

确认范围：

- Windows 真实 Python 执行自写函数、列表调用及标准输入，中文输出换行正常；语法错误、超时和输出过多有明确执行事实。
- 正式 QML 按钮与快捷键运行当前代码；revision B 不再显示 revision A 的 PASS，执行输出面板底部进入可见区域。
- Codex/API 两条 UI 路径均可一次提交锁定代码、接收主观评价、完成本场并生成复盘；这些测试的 AI 传输使用替身，不证明真实服务当前可用。
- 不要求公开单测通过才能评价代码；测试断言 AI 来源与空 `coding_evidence`，防止将主观部分得分伪装成 Grader PASS。

独立只读复核 `checkpoint_acceptance` 未发现阻断项。复核了 `.y`、CRLF 规范化、共用 revision 更新及评分来源分支；指出滚动测试只检查底边，主 Agent 因此实际查看了以下四张正式页面截图：

`workspace/maintainer/agent-runs/interview-depth-20260908-retest/`

- `self-run-codex.png`、`self-run-provider.png`：深/浅色执行页。输出标题、退出码、revision 和结果 9 可见；运行、公开测试、提交按钮均在窗口内。自动滚动后编辑器上部在视口之外，可以向上滚回，不是代码被清空。鼠标停留在运行按钮时存在快捷键 Tooltip，不能把它当成正文重叠。
- `self-run-report-codex.png`、`self-run-report-provider.png`：深/浅色复盘页，评分来源、证据和下一场入口可见；长报告仍通过滚动查看。

截图来自 1080×680 逻辑窗口，Windows 缩放下 PNG 为 1350×850；均使用隔离合成档案。截图中的连接状态和分数属于测试场景，不用于宣称真实 Codex/API 连接成功或面试质量达标。未重新生成其他尺寸截图；此前四尺寸测试记录保留，不扩充其证明范围。

### 人工验收交接

从 [桌面源码启动说明](../../docs/desktop-app.md#源码运行) 启动，继续使用原来的 `manual-uat` 目录，不重置档案、连接或材料。为使用新的冻结评分规则，请新开一场，不改写旧场次。

1. 选择真实可用的面试官、岗位与困难难度，确认本场材料范围；自我介绍之后连续使用「提交并继续」。检查一个方向挖深后会转向其他经历角度，再进入四个相关原理主题，且每次只展示下一问。
2. 进入手撕后自行编写函数和样例，按「运行代码」，确认能看到 `print` 输出；公开单测是独立可选入口。
3. 修改代码后旧测试结果不得作为当前 PASS；允许不完整代码直接「提交给面试官」，确认复盘区分逻辑评价、实际运行与公开测试事实。

剩余限制：真实模型延迟及主题深度仍需真人验收，上一轮 Codex 三次探针各约 125–127 秒；阶段最低轮数不等于语义主题去重保证；本地执行不是恶意代码沙箱；旧场次不迁移重写。本次没有读取真实 Profile/材料/Key，没有调用真实模型，没有重启或关闭用户应用；没有运行全量 pytest、CI、Windows/macOS 构建，没有合并 main、Tag 或 Release。
