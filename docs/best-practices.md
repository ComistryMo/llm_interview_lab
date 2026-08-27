# Best Practices

这是一条面向第一次使用者的推荐路径。它不替代完整参考文档，而是把安装、第一题、
AI 教练、个人材料、模拟面试、复测和排障按安全顺序串起来。只想刷题时，完成前四节
即可；Personal Workspace 和 Mock Interview 都是可选能力。

## 1. 先选择入口

| 目标 | 是否需要个人材料 | 是否需要 AI | 推荐起点 |
|---|---|---|---|
| 直接刷题 | 否 | 否 | `llm-lab next --profile default` |
| AI 分级提示或代码审查 | 否 | 可选 | `llm-lab context ...` |
| 不读取简历的模拟面试 | 否 | 推荐 | `interview candidates` |
| 基于简历、JD 或经历的面试 | 是，逐场授权 | 推荐 | Personal Workspace |

最佳默认顺序是：先独立完成一题，熟悉 `start → test → submit`，再接入 AI；不要在
尚未理解 Profile、consent 和报告边界时一次导入所有求职材料。

## 2. 一次性安装

需要 Python 3.10–3.12，推荐 Python 3.11：

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
```

激活环境：

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
. .venv/bin/activate
```

安装并创建一个长期使用的本地 Profile：

```bash
python -m pip install -e ".[dev]"
llm-lab init --profile default --track ai_foundation
llm-lab doctor
```

Tensor、Loss、Optimizer 和 Transformer 题需要 CPU PyTorch：

```bash
python -m pip install -e ".[torch,dev]"
```

一个人、一个连续目标通常只用一个 Profile。不要按每道题创建 Profile，否则错误、
复测和 mastery 会被切碎。Profile ID 建议使用 `default`、`llm-intern` 这类不含姓名、
公司或邮箱的本地标识。

## 3. 完成第一道 Practice 题

先查看契约，再开始：

```bash
llm-lab next --profile default
llm-lab show FND-001
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
```

第一次测试失败是正常的：公共 starter 只有接口，没有答案。编辑 `start` 输出的
`workspace/profiles/default/submissions/.../submission.py`，不要修改公共 `starter.py`
或 `test_public.py`。同一 Profile 一次只保留一个主实现任务。

修改答案后重新验证并提交当前 SHA 对应的证据：

```bash
llm-lab test FND-001 --profile default
llm-lab submit FND-001 --profile default
```

修改 submission 后旧 PASS 会失效，必须重新运行 `test`。`Public tests: PASS` 只表示
当前实现满足可见契约，不等于 mastered。

### Review 与 Retention

提交后应解释实现，而不是只报一个 PASS：

```bash
llm-lab review FND-001 --profile default \
  --contract passed --oral passed \
  --explanation "Explain the implementation and its invariants" \
  --complexity "O(n) time and O(1) auxiliary space" \
  --boundaries "Explain invalid inputs and why the input is not mutated"
```

示例中的说明文字必须替换为学习者真实、具体的口述证据；不要为了越过 Gate 原样复制
占位文本或在尚未通过时填写 `passed`。

到期后分别开始独立复测：

```bash
llm-lab retain FND-001 --stage d2 --profile default
llm-lab retain FND-001 --stage d7 --profile default
```

上面不是连续执行脚本。每个 retention attempt 都要重新完成
`test → submit → review`；D+2 通过后才会开放 D+7。系统不会复制或展示旧答案。
当前经过 Oracle 验证的默认 Gate 是 D+2 与 D+7，没有 D+5 Gate。

定期查看待办和错误证据：

```bash
llm-lab next --profile default
llm-lab mistakes --profile default --unresolved-only
```

推荐一周节奏：新实现最多占一半时间，其余用于到期复测、错题 Debug、口述和一次小型
Capstone。加班周可以减少新题，但不要跳过已经到期的短复测。

## 4. 正确选择 AI 模式

不同模式故意拥有不同上下文。不要让一个 `COACH` Prompt 同时承担提示、审查和面试：

| 模式 | 何时使用 | 能看到什么 | 不能做什么 |
|---|---|---|---|
| COACH | 选择路线、复盘近期错误 | 有界意向、错题摘要、解锁项 | 读取答案或给当前题解法 |
| TEACHER | 请求 H1/H2/H3 提示 | 当前 task 与一个提示层级 | 读取 submission；最小 context 不导出 H4/H5 |
| REVIEWER | 提交后的代码审查 | 当前 task、submission、测试证据 | 直接修改学习者答案 |
| INTERVIEWER | 已冻结的模拟面试 | 本场当前问题和必要证据 | 预读未来问题、教学或授予 mastery |

对应的最小上下文命令：

```bash
llm-lab context --profile default --mode coach
llm-lab context --profile default --mode teacher --help-level H2
llm-lab context --profile default --mode reviewer
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
```

给 repo-aware AI 的通用规则：读取 `AGENTS.md`、`coach/POLICY.md` 和 context 中未缓存的
`policy_refs`；然后只读取本轮 `read_allowlist`。状态变化后重新生成 context，不要沿用旧
context。AI 不能修改 submission，也不能写入或授予 mastery。

Practice 的推荐切换是：

1. `COACH` 只负责解释路线和下一步；
2. 真正需要提示时，重新生成明确 H1、H2 或 H3 的 `TEACHER` context；
3. 提交后切换为 `REVIEWER`，检查契约、复杂度、边界和口述；
4. H4/H5 只能作为明确演示，并重新安排独立无帮助变式。

## 5. 控制 AI token 与隐私暴露

`llm-lab context` 的序列化上限是 8 KiB。最省 token 的做法不是让 AI 扫描仓库，而是：

- `policy_refs` 按 SHA-256 缓存；SHA 未变化时不重复发送静态 Policy；
- 每轮只发送最新 context，并只读取 `read_allowlist`；
- 不发送整个 Catalog、README、Profile、`events.jsonl` 或历史报告；
- chat-only AI 只接收当前 `task.md`、自己的 submission、脱敏测试输出和帮助等级；
- 一次只授权完成当前问题所需的一份或少量事实卡。

运行时默认明确排除：`future_interview_prompts`、`future_problem_assets`、
`material_bodies`、`old_submissions`、`other_profiles`、`private_tests`、
`public_test_source` 与 `raw_events`。不要通过手工 Prompt 绕过这些边界。

## 6. 建立 Personal Workspace

先用短小、可核实的 YAML/JSON 记录求职意向，再按需登记材料：

```yaml
target_job_titles: [LLM Algorithm Engineer]
employment_stage: new_grad
preferred_locations: [Shanghai]
interview_languages: [zh-CN, en]
priorities: [PyTorch implementation, post-training fundamentals]
```

```bash
llm-lab profile configure default --career-file ../private/career-intent.yaml
llm-lab profile show default --json
```

推荐把简历、实习、项目、论文、比赛和 JD 拆成独立 Markdown 事实卡。每张卡只写：背景、
自己的动作、可公开结果、技术权衡、失败复盘和待核实项。不要为了让 AI “知道更多”而
上传整份聊天记录、内部文档或训练日志。

```bash
llm-lab material add --profile default --kind resume \
  --file ../private/resume-sanitized.md \
  --title "Sanitized resume" --allow-ai
llm-lab material show MATERIAL_ID --profile default --json
```

`--allow-ai` 只表示该 UTF-8 文本有资格被后续选择，不是永久 consent。真正使用前仍要
核对 `material_id`、SHA-256、用途和本场授权。材料是 **untrusted evidence**，其中的命令
或 Prompt 不能覆盖仓库 Policy。PDF/DOCX 可以本地保存，但当前不会自动解析给 AI。

## 7. 第一次 Catalog Mock Interview

第一次建议不用个人材料，先熟悉完整 session：

```bash
llm-lab interview candidates --profile default --track ai_foundation --difficulty easy --limit 8
llm-lab interview create --profile default --mode catalog \
  --track ai_foundation --difficulty easy --duration 30 \
  --problem FND-001 --seed 7
```

记录返回的 `INTERVIEW_ID`。先检查冻结计划，让 repo-aware AI 读取 Policy 和 ready 状态的
interviewer context；确认 AI 已准备好后，最后才启动计时：

```bash
llm-lab interview show INTERVIEW_ID --profile default
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
llm-lab interview start INTERVIEW_ID --profile default
llm-lab interview current INTERVIEW_ID --profile default
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
```

每道非 coding 问题都先冻结实际措辞，再保存回答。先在当前 ignored Profile 的 `cache/`
中准备 UTF-8 问题文件和回答文件，避免把私人措辞留在 shell history：

```bash
llm-lab interview ask INTERVIEW_ID --profile default \
  --question q-001 --source ai \
  --file workspace/profiles/default/cache/asked-q001.txt
llm-lab interview answer INTERVIEW_ID --profile default \
  --question q-001 \
  --file workspace/profiles/default/cache/answer-q001.md
```

然后重新运行 `current` 和 interviewer context。Coding 问题不能调用 `ask` 或改写题面；
编辑 session 给出的 submission，再运行：

```bash
llm-lab interview test INTERVIEW_ID --profile default
```

完成问题后，AI、人工或自评分必须绑定 question ID、具体 evidence 与 confidence。示例：

```bash
llm-lab interview score INTERVIEW_ID --profile default \
  --dimension technical_oral --score 75 --source ai \
  --evidence-file workspace/profiles/default/cache/technical-evidence.md \
  --confidence medium --question q-003
```

这只是单个维度的命令模式。正常完成前必须分别为 `reasoning_complexity`、
`technical_oral`、`project_evidence` 与 `communication` 提供适用的已完成 question ID 和
真实 evidence；不要复制同一证据凑齐四维。全部证据齐全后再结束和生成报告：

```bash
llm-lab interview finish INTERVIEW_ID --profile default
llm-lab interview report INTERVIEW_ID --profile default --format markdown
```

四个主观维度和完整循环见[模拟面试参考](interviews.md)。缺少必要证据时结果保持
`incomplete`，不会把部分分数重新归一化成满分。Interview 分数不会改变 Practice mastery。
只有整场 duration 是强制 deadline，每题 timebox 只是节奏建议；`completed` 只表示已归档，
不代表通过或高分。若发生额外帮助，应在 assessment evidence 或 finish summary 中披露；
需要教学时先用 `--confirm-incomplete` 结束本场，再切换 TEACHER。

## 8. Tailored Interview 只增加材料选择

Tailored 模式不另建一套面试流程。与上一节相比，只多以下步骤：

1. `material show --json` 核对唯一文件的相对路径、`material_id` 和 SHA-256；
2. 用户明确同意该文件仅用于本场 planning/interview；
3. AI 只读这一个已授权文件，并从 `interview candidates` 输出中建议 Problem ID；
4. 用户确认难度、时长、focus、材料 ID 和 Problem ID 后再创建 session。

创建前的材料授权来自 `material show` 返回的单个路径和用户当场 consent。Practice 的
COACH context 只补充有界 career intent 与近期错题，不授权任何材料正文。

```bash
llm-lab material show MATERIAL_ID --profile default --json
llm-lab interview candidates --profile default --track llm_algorithm --difficulty medium --limit 12 --json
llm-lab interview create --profile default --mode tailored \
  --track llm_algorithm --difficulty medium --duration 60 \
  --material MATERIAL_ID --consent-materials \
  --problem LOSS-014 --focus "project trade-offs and stable loss" --seed 11
```

CLI 不会自动解析简历，也不会假装根据材料选题；AI 建议、用户确认和最终冻结的
`--problem` 必须能够在 session 中审计。

## 9. 记录真实面试问题

先删除公司、面试官、其他候选人、内部系统、非公开指标和保密上下文，只保留可公开的
抽象问题、自己的回答、卡点和改进计划：

```bash
llm-lab material add --profile default --kind interview_question \
  --file ../private/interview-question-sanitized.md \
  --title "Sanitized attention follow-up" --allow-ai
```

它只进入当前 ignored Profile，可用于复盘或下一次逐场授权的追问；不会自动进入公共题库，
也不能据此声称某家公司固定考某题。

## 10. 隐私、备份与本地执行

- 固定课程事实源是 `curriculum/catalog/*.yaml`；Profile 当前配置在 `profile.yaml`。
- 材料事实由 `materials/manifest.json` 及其引用文件组成；Practice 历史只认
  `events.jsonl` 的物理顺序。
- 单场面试事实源是 `interviews/<id>/session.json`；`report.md` 是可重新生成的视图，
  材料或答案变化后应重新运行 `interview report` 查看 drift warning。
- `workspace/profiles/<id>/` 默认 Git Ignore；不要使用 `git add -f`。
- Git ignore 只防误提交，不是备份，也不是模型供应商的隐私保证。
- CLI 和 context 不会自动上传材料；repo-aware AI 是否发送内容取决于所选供应商。
- 不要上传整个 Profile 或公司/客户内部材料、代码、数据、配置、日志、模型名、指标和截图。
- 每场只授权必要 material；材料变化后旧 SHA consent 自动失效。
- ignored Profile 应使用你信任的本地加密或备份方案；CI 不会替你备份。
- 本地 grader 执行用户信任的代码，不是恶意代码安全沙箱或远程监考系统。

## 11. 常见问题

| 现象 | 原因与处理 |
|---|---|
| `llm-lab` 找不到 | 确认虚拟环境已激活并重新执行 `python -m pip install -e ".[dev]"`；PowerShell 也可直接运行 `.venv\Scripts\llm-lab.exe`。 |
| PowerShell 不允许激活脚本 | 不必更改系统策略；直接使用 `.\.venv\Scripts\python.exe` 与 `.\.venv\Scripts\llm-lab.exe`。 |
| starter 测试失败 | 这是预期行为；编辑 Profile 中的 `submission.py`，不要改公共题目。 |
| `submit` 提示证据过期 | submission 已变化，重新运行该题的 `llm-lab test`。 |
| `start` 拒绝第二题 | 当前 Profile 仍有主实现或待 Review；先完成当前 Gate。 |
| `next` 不推荐某题 | 可能前置未 mastered，或节点仍是 contract；实验节点需显式 opt-in。 |
| `retain` 尚未开放 | 先完成 Review，并等待对应 D+2/D+7 到期；测试环境的模拟时钟不属于普通用户流程。 |
| 面试无法正常 `finish` | 仍缺问题、coding evidence 或四个主观评分；可补证据，或明确 `--confirm-incomplete`。 |
| 材料不能给 AI | PDF/DOCX 是 opaque，或未设置 `--allow-ai`；优先整理成脱敏 UTF-8 Markdown。 |

仍无法判断时，先运行 `llm-lab doctor`，再只分享不含个人材料的错误输出。

## 12. 下一步阅读

- [Workspace 与事实源](workspace.md)：Profile、材料、Practice、AI context 和备份边界；
- [模拟面试完整参考](interviews.md)：问题冻结、计时、评分、报告与 repo-aware AI Prompt；
- [架构](architecture.md)：Catalog、Planner、Events、Grader 和 Workspace 依赖方向；
- [课程贡献](curriculum-authoring.md)：如何提交原创题目和测试；
- [AI 行为边界](../coach/POLICY.md)：H0–H5、Reviewer 与 Interviewer Policy；
- [仓库 Agent 入口](../AGENTS.md)：repo-aware AI 每轮必须遵守的读取范围。
