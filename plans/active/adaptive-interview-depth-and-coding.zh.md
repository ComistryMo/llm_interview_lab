# 动态面试：多角度深挖与自由手撕

基线：`dbc9aba`，开发分支 `fix/dynamic-interview-full-flow-20260905`。

## 目标与当前事实

用户要求：项目不能只追一个方向；经历后需要 3–4 道相关八股；困难体现提问深度和广度，不是评分宽容度；手撕可运行自己写的 Python 样例，未完成代码也能交面试官评逻辑。

当前 `interview_flow.next_stages` 将经历和原理各限制为 2–4 轮；策略文件仅建议概述后一到两轮深入。`role_interviews` 的代码评分只接受 Grader 通过=5/失败=1，Controller 也拒绝 AI 评 coding。这些是本次明确改变的产品语义，不是增加更多固定题。

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
- 进度：主要实现完成；用户要求尽快关机，保存检查点，最后两行修复尚未复测。

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
