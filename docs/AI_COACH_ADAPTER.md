# AI 教练接入指南

本项目采用“一份权威协议 + 薄适配层”。`docs/COACHING_PROTOCOL.md` 定义行为，`AGENTS.md` 是支持项目规则发现的 coding agent 入口。Codex 对该文件的发现与覆盖顺序见 [OpenAI 官方 AGENTS.md 指南](https://developers.openai.com/codex/guides/agents-md/)。本页不宣称任何未实测产品获得完整支持。

## 三种能力模式

### 能读写仓库并运行终端

按固定顺序读取规则，先运行只读状态与测试命令。只有用户授权修改训练基础设施时才写相关文件；`src/` 始终需要单独明确授权。审查后追加 ledger，不覆盖历史。

### 能读文件但不能运行终端

读取同样的最小文件集，让学习者运行命令并提供退出码和精简输出。不得把用户转述当作自己运行过的证据。

### 纯聊天助手

学习者提供：教练协议、去敏的 learner profile、当前 Task Card、答案 diff、测试摘要。助手只做离线审查与口述，不维护仓库状态；结果通过 handoff 交回有文件权限的教练。

### 外部官方作业

先读取对应 `curriculum/external/` Task Card 和上游当前政策。Stanford CS336 companion assignment 的最高帮助为 H2：助手可以解释非步骤化概念、低层 API 或错误类别，但不得生成代码/伪代码、补 TODO、编辑外部 checkout、替用户执行作业命令或计算待提交答案。用户对原生任务的 H5 授权不能覆盖这一限制。

助手只能核对用户亲自提供的命令、环境和结果；未运行的 GPU、服务或数据实验必须写 `not_run`。若要演示相同概念，改用不同接口、不同数据和独立测试的 clean-room 原生题。

五个 assignment ID 只是聚合 Gate。AI 应从生成导航选择一个 canonical problem-group ID，并在用户明确开始后确认它是私人 ledger 的唯一 `CURRENT_TASK`；不得把安装 checkout 当成开始任务、通过前置或掌握。A2/A4 含 A1 staff material，未确认 A1 Gate 与 spoiler 风险时必须停止安装指导。

需要发现外部任务时，优先运行 `python scripts/manage_external_course.py list --json`、`show <assignment-id> --json`，再以 `show-group <canonical-id> --json` 取得当前 group 的 problem、capability、evidence、runtime 与 retention 契约；不要从人类可读表格猜字段，也不要把整份 assignment 当成一个 Task。机器输出不含本机绝对路径，也不能取代用户对上游政策与依赖的人工阅读。

AI 不应手改 append-only ledger。具备终端权限的教练只能先调用 `python scripts/select_current_task.py <task-id>` 预览。当前 CS336 assignments 为 `inventory-audited`，原生 readiness 尚未机器映射，外部 canonical ID 必须 fail closed、不得加参数绕过；只有后续受审查元数据把它升级为 `implementation-ready` 后，才可按选择器提示申请显式应用。选择器只登记任务，不生成实现证据。外部状态始终只表示 companion runtime；official runtime 的执行结果必须另行审查，不能由 `mastered` 推定。

## 最小上下文集合

1. `docs/COACHING_PROTOCOL.md`；
2. `state/CURRENT_TASK.md`；
3. 当前 `curriculum` Task Card；
4. 相关 diff 与定向测试摘要；
5. 必要时再读 `state/LEARNER_PROFILE.md` 和最近一次 review。

不要一次上传整个仓库，尤其不要上传 `notes/`、日志或本机配置。

## 标准指令

开始训练：

```text
按教练协议开始当前唯一 Task。先核对状态和定向测试，不修改答案；
只给一个下一步，不提前解锁。
```

审查：

```text
审查当前 diff 和文字需求，运行或核对定向测试。不要改 src。
给结论、证据、最多三个问题、我要回答的问题、唯一下一步和测试命令。
```

提示：

```text
我已独立尝试至少 25 分钟。给 H2 概念提示；不要给步骤、伪代码或代码。
```

考试：

```text
开始 D+2 闭卷复写。不要展示旧代码或提示，使用等价但不同的测试验收。
```

## 个性化可以改变什么

可以改变岗位方向、时间预算、任务语境、题量、Preview Lane 和考试日期；不能改变单一主任务、帮助记录、H4/H5 限制、D+2/D+7 和隐私红线。

## 每轮自检

- 是否只推进一个 Implementation Task？
- 是否在没有授权时写了学员答案？
- 是否把测试全绿误写为 mastered？
- 是否记录了最高帮助等级？
- 是否把未知项目事实标为“待核实”？
- 是否明确哪些命令没有运行？
