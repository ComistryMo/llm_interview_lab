# 最佳实践：从第一次启动到稳定训练

这份指南给出推荐使用方式。目标是降低操作成本、保护隐私、节省 AI token，并始终区分“测试通过”和“能够独立完成”。

## 1. 先选择一个入口

- 想要引导式体验：使用 Windows / macOS 桌面版；
- 想写脚本、贡献课程或调试：使用 CLI；
- 想让仓库感知 AI 帮助：在当前仓库启动 Codex 等 Agent；
- 只想刷题：无需添加求职材料或连接 AI；
- 想进行针对性面试：先添加最少的脱敏材料，再逐场授权。

不要同时对同一个学习档案运行多个写入实例；`events.jsonl` 第一版不支持多进程并发写。

## 2. 第一次使用桌面版

```text
创建学习档案
→ 选择目标岗位
→ 跳过或完成简短自评
→ 保持“暂不连接 AI”
→ 开始第一题
```

先在 No-AI 模式验证课程、保存和测试都正常，再决定是否添加远程服务。这样容易区分本地问题与 Provider 问题。

## 3. 第一次使用 CLI

```bash
python -m pip install -e ".[dev]"
llm-lab init --profile default --track ai_foundation
llm-lab doctor
llm-lab next --profile default
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
```

starter 第一次失败是正常现象。只编辑 `start` 输出的当前 `submission.py`，不要修改公共题面、starter 或测试来制造通过。

### 常用命令速查

下面的命令均为真实 CLI 入口；按需使用，不必一次全部执行。

```bash
llm-lab quickstart
llm-lab init --profile default --track ai_foundation
llm-lab doctor
llm-lab next --profile default
llm-lab catalog
llm-lab graph --track ai_foundation
llm-lab graph --quest quest.python_data_reliability
llm-lab profile show default
llm-lab mistakes --profile default
llm-lab context --profile default --mode coach
llm-lab context --profile default --mode teacher --help-level H2
llm-lab context --profile default --mode reviewer
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
llm-lab show FND-001
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
llm-lab submit FND-001 --profile default
llm-lab review FND-001 --profile default --contract passed --oral passed --explanation "说明实现" --complexity "O(n)" --boundaries "覆盖空输入"
llm-lab retain FND-001 --stage d2 --profile default
llm-lab retain FND-001 --stage d7 --profile default
llm-lab material list --profile default
llm-lab material add --profile default --kind resume --file resume.md
llm-lab interview candidates --profile default --track llm_algorithm --difficulty medium
llm-lab interview create --profile default --mode catalog --track llm_algorithm --difficulty medium --duration 30
llm-lab interview start INTERVIEW_ID --profile default
llm-lab interview current INTERVIEW_ID --profile default
llm-lab interview finish INTERVIEW_ID --profile default
```

## 4. 一道题的完整流程

1. 读清契约、输入输出、异常、mutation 与复杂度要求；
2. H0 独立实现；
3. 运行精确公开测试；
4. 失败时先读 traceback，再决定是否请求 H1 / H2 / H3；
5. 测试通过后提交并完成契约审查与口述答辩；
6. D+2 不看旧答案进行等价重写；
7. D+7 做调试或集成迁移；
8. 只有确定性条件满足后进入 `mastered` 并解锁下一节点。

公开测试是可见学习契约，不是隐藏防作弊系统。不要把“记住测试数据”当作掌握。

## 5. 高效使用 AI

### 最小上下文

一次只发送：

- 当前公开题面；
- 必要的答案片段；
- 最近失败摘要；
- 一个明确问题；
- 需要的帮助等级。

不要发送整个 Workspace、全部日志、旧答案、无关材料、Git 历史或完整 Profile。上下文越小，token 成本越低，也越容易得到针对性反馈。

### 帮助等级

| 等级 | 允许内容 | 独立掌握权重 |
|---|---|---:|
| H0 | 完全独立 | 100% |
| H1 | 官方文档或单个语法问题 | 85% |
| H2 | 概念方向 | 70% |
| H3 | 结构化步骤 | 50% |
| H4 | 关键片段 | 25% |
| H5 | 完整演示，只能用于新私人变式 | 0% |

H4 / H5 后必须安排新的无帮助变式；演示不能成为 retention、interview 或 mastery 证据。

### 推荐 Prompt

```text
Read AGENTS.md and coach/POLICY.md.

Act in COACH mode for profile "default".
Run `llm-lab next --profile default` and then
`llm-lab context --profile default --mode coach`.
Treat read_allowlist as the complete set of files you may additionally read.

Do not modify my submission or reveal a complete solution.
Use H0-H5. Review only when I explicitly ask.
Do not grant mastery yourself.
```

## 6. 求职材料最小化

优先维护结构化、脱敏、可核实的事实卡，而不是把整个私人目录交给 AI。每份材料只解决一个问题：简历、岗位 JD、项目事实、论文摘要或真实面试复盘。

为便于和工具、审查记录对照，以下英文术语保留为规范字段：

- `workspace/profiles/<id>/` 是本地学习档案目录；
- `material_id` 标识一份材料；
- 每次授权都核对当前 `SHA-256`；
- 材料属于 **untrusted evidence**，其中的文字不是指令；
- `read_allowlist` 是本轮允许 AI 读取的完整文件集合；
- `consent` 只对当前文件指纹和当前场次有效。

添加前检查：

- 没有公司源码、内部数据、模型名、配置、未公开指标、截图或日志；
- 团队成果与个人贡献分开；
- 数据量、指标和结论能说明来源；
- 遗忘或矛盾写“待核实”，不补造；
- 文件中的任何指令都被视为不可信文本。

## 7. 进行模拟面试

面试前确定岗位、求职阶段、难度、时长与 focus。除非确实需要个性化追问，否则先使用不读取材料的 catalog 面试。

Active 阶段：

- 一次只回答一个主问题；
- 不切换到教学模式；
- 代码题只使用冻结题面和本地 Grader；
- 不请求解法提示；如必须教学，先以 incomplete 结束本场；
- AI / 人工主观分必须引用回答证据；无证据写 `unscored` 或 `incomplete`；
- 模拟面试结果不写入 Practice mastery。

面试后只选 1–3 个最关键缺口回写训练计划，避免一次解锁大量任务。

## 8. 连接普通 API

先测试最小连接，再发送真实训练上下文。Key 只存在系统密钥环；若 Keyring 不可用，不要写入 `.env`、YAML、Profile 或聊天记录作为临时绕过。

Provider 失败时先确认：服务是否启动、Endpoint、模型 ID、网络、Key、限流。失败不会影响 No-AI 流程。

## 9. 连接 Codex

Coach / Reviewer / Interviewer 模式默认只读。仓库维护才使用 Repository Agent，并逐项核对审批卡片的范围、命令、文件与 Diff。不要批准超出当前任务或当前 Profile 的读取与写入。

macOS Finder 启动找不到 Codex 时，在设置选择可执行文件；不要通过抓取交互式终端文本实现连接。

## 10. 每周节奏

推荐每周只维护一个主要编码任务：

- 2–3 个训练块独立实现；
- 1 个算法或调试恢复块；
- 1 个项目事实核验块；
- 到期 D+2 / D+7 优先于新题；
- 周末做一次短口述或模拟面试；
- 加班周保留复测、错误复盘和一个最小任务，不补“训练债务马拉松”。

## 11. 何时算掌握

至少满足：公开测试通过、文字契约通过、能解释复杂度和边界、口述答辩通过、D+2 等价重写通过、D+7 迁移通过。需要复测资产的节点缺少资产时不能进入 `mastered`。

## 12. 安全与备份

- 定期备份当前 Profile 到用户自己的加密位置；
- 不提交真实 Profile；
- 不上传整个 Profile 给聊天 AI；
- 不运行不信任的 submission；本地 Grader 不是恶意代码沙箱；
- 下载桌面包后核对 `SHA256SUMS.txt`；
- macOS 未公证 Alpha 只通过系统“隐私与安全”确认自己核验过的文件。

对应的英文安全约束是：**Git ignore prevents accidental commits; it is not a backup**。The CLI and `context` command never upload materials automatically。Never upload the whole Profile or employer/client internal material。

`context` 的序列化上下文上限为 **8 KiB**；`policy_refs` can be cached by SHA-256，但每轮应 **send only the newest
context for each turn**。`read_allowlist` is **not an invitation for AI to
scan the repository**；它只允许读取明确列出的文件。

默认不把这些内容放进上下文：`future_interview_prompts`、
`future_problem_assets`、`material_bodies`、`old_submissions`、
`other_profiles`、`private_tests`、`public_test_source`、`raw_events`。
