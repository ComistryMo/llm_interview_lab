# Architecture

LLM Interview Lab 是 local-first、clone-first 的确定性训练核心。一个 Profile 内有三个入口，但它们共享同一套固定 Catalog 和隐私边界：

```text
                         curriculum/catalog/*.yaml
                            /                 \
                           /                   \
Personal Workspace   Practice lifecycle    Mock Interview
materials/manifest   planner + grader      frozen session plan
        |                    |              timer + local grader
        |              events.jsonl                |
        |                    |               fixed rubric
        +--------------------+---------------------+
                             |
                     CLI / one BYO AI coach
```

这三个入口不是三个服务或运行时 Agent：

- **Personal Workspace** 保存显式登记的本地求职材料。材料 manifest 只引用当前 Profile 内的文件和 SHA-256；AI 只能读取本场明确 consent 的 ID。
- **Practice** 负责 DAG、公开测试、Review、Retention 和 mastery。`events.jsonl` 仍是 Practice 历史事实源。
- **Mock Interview** 从已验证的固定题库选择 coding 题，冻结难度、时长、题目、材料、fingerprint、seed 和 rubric。每场 `session.json` 是该面试的事实源，`report.md` 是可重新生成的视图。

Interview 不追加 Practice evidence，不产生 Review、Retention 或 mastery。两者只共享 Catalog 元数据和底层本地 grader；模拟分数永远不能解锁课程节点。

## 核心模块边界

`catalog.py` 读取 Problem、Track、Quest、Capstone；`dag.py` 只处理学习依赖；`workspace.py` 管理 ignored Profile；`submissions.py` 是 Practice 与 Interview Python 答案共用的唯一 loader；`grader.py` 用独立 pytest 子进程、超时和输出截断产生客观证据；`events.py` 负责 Practice append/reduce；`lifecycle.py` 验证 Review、retention 和 mastery；`cli.py` 只协调规则。

面试复用 Catalog 和 grader，但使用 interview-local submission 与 session。Coding 选择必须满足 `ready` 且 validation 为 `oracle`、`field` 或 `stable`。学习 prerequisites 用于课程解锁，不作为诊断面试的绝对门禁。

面试总分由版本化固定 rubric 聚合。测试状态、passed/failed、duration 和 submission SHA 属于 objective evidence；reasoning、technical oral、project evidence 与 communication 等主观维度必须带 source、evidence 和 confidence。证据缺失时结果为 `incomplete`，不得重新归一化出完整分数。

## AI 在边缘

AI 可以根据用户明确授权的材料与目标 Track 排序候选题、逐题追问、评估主观 rubric、解释报告和推荐后续固定节点。AI 不能修改固定 Catalog、替代 grader 或 clock、改变 rubric、自动上传材料、授予 mastery，或把临时生成题加入公共题库。

材料内容是 untrusted evidence，不是控制面。嵌入材料的指令、路径、链接、代码或宏均不得触发工具调用；材料也不能覆盖 `AGENTS.md` 或 `coach/POLICY.md`。

## 事实源

- 固定课程：`curriculum/catalog/*.yaml`。
- Practice 历史：每个 Profile 的 `events.jsonl`，按物理顺序归约。
- 个人材料：当前 Profile 的 `materials/manifest.json` 与其引用文件。
- 单场面试：`interviews/<interview_id>/session.json`；Markdown 报告是 generated view。

pytest 是 Runner；fixture、闭式公式、框架参考、brute force、交叉实现或 property 是课程 Oracle。AI 主观评价既不是测试 Oracle，也不是 mastery Gate。

项目不包含 Web、数据库、账户、网络服务、多 Agent Runtime、远程上传、恶意代码沙箱或防作弊监考。External course pack 是冻结的兼容元数据，不进入默认 DAG 或模拟面试题池。
