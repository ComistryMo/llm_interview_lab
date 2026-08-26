# 外部课程包

外部课程包把公开课程接入本仓库的训练与复测流程，但**不把第三方仓库变成本项目的一部分**。本项目只提交独立编写的元数据、导航、教练 Task Card 和安全工具；官方代码、测试、PDF、数据、模型与答案留在官方仓库，由用户按需检出到 Git 忽略的 `.external/`。

当前提供 Stanford CS336 Spring 2026 course site 所链接五份 assignment 的 companion track。它是独立的兼容与教练层，不隶属于 Stanford，也不代表 Stanford 认可或认证本项目。课程页链接的 A1 固定仓库 README 自称 Spring 2025 artifact；本项目保留这一来源差异，不把 artifact 年份改写成 2026。

## 为什么不是直接复制

“能完成全部作业”和“有权在 Apache-2.0 仓库再分发全部材料”是两件事。当前审计版本中，Assignment 1–4 根目录包含 MIT LICENSE；对 Assignment 5 的固定 Git tree 递归检查未发现名为 LICENSE、COPYING 或 NOTICE 的文件。这是负面审计结果，不是法律意见或授权。因此，本仓库不复制任何一份 assignment 的正文或实现材料，也不对 Assignment 5 推定再分发许可。A5 只登记互操作和审计必需的事实性标识（名称、路径、命令和计数），不复制正文、实现、测试体、prompt、fixture 或答案。

这种设计还避免三类问题：上游作业更新后悄然漂移、官方答案混入学员证据，以及公共训练仓库替在读学生完成受考核作业。

## 使用流程

需要 Python 3.10+ 与 Git 2.23+。Windows 用户直接运行下列 Python 命令；Makefile 只是 Unix 环境的快捷入口。

先在本仓库查看已经固定和审计的清单：

```bash
python scripts/manage_external_course.py list
python scripts/manage_external_course.py show EXT-CS336-A1
```

AI 助手或其他工具应优先读取 machine-readable 输出，避免解析人类文案：

```bash
python scripts/manage_external_course.py list --json
python scripts/manage_external_course.py show EXT-CS336-A1 --json
python scripts/manage_external_course.py show-group EXT-CS336-A1-tokenizer-core --json
```

assignment 级 `show` 用于清单与聚合 Gate；canonical `show-group` 是交给 AI 或教练的最小任务上下文，包含该 group 的 problem IDs、能力、验收证据、相关命令、同 assignment 前置 group、runtime 与 D+2/D+7 契约。这里的 group 依赖是本 companion 为小步训练定义的顺序，不声称是 Stanford 官方课程规则。JSON 只包含公共来源、治理、资源与任务元数据以及 `missing/valid/invalid` checkout 状态，不输出本机绝对路径。

阅读对应 Task Card、上游许可证与学术诚信政策。确认后只检出需要的 assignment：

```bash
python scripts/manage_external_course.py install EXT-CS336-A1 --acknowledge-policy
```

每次只能安装一份，安装不是开始任务，也不证明前置 Gate 已通过。A2 和 A4 的 checkout 含 A1 staff implementation；只有自己的 A1 集成 Gate 已通过，才可单独确认剧透风险：

```bash
python scripts/manage_external_course.py show EXT-CS336-A2
python scripts/manage_external_course.py install EXT-CS336-A2 --acknowledge-policy --acknowledge-spoilers
```

安装器无法验证学习者是否真的通过 A1 Gate；`--acknowledge-spoilers` 只是明确的自我声明。为避免一次暴露全部答案来源，`install --all` 不存在。

安装器执行以下有限动作：

1. 从 manifest 登记的官方 HTTPS 地址检出固定 40 位 commit；
2. 在 `.external/stanford-cs336/<assignment>/` 建立独立 Git 工作树；
3. 记录不可漂移的 upstream ref，创建 `learner-work` 分支；
4. 禁用官方 `origin` 的 push URL，防止误推；
5. 验证来源身份后停止，不安装依赖、不执行脚本、不运行第三方测试。

随时检查身份和本地修改。默认输出仓库相对路径，便于分享日志时不泄露本机用户名和目录结构：

```bash
python scripts/manage_external_course.py status EXT-CS336-A1
python scripts/manage_external_course.py verify EXT-CS336-A1
python scripts/manage_external_course.py commands EXT-CS336-A1
```

`commands` 只打印审计时登记的上游命令。运行前仍须亲自检查依赖、脚本、数据下载、费用和设备要求。若需要备份答案，应给这个独立 checkout 配置你自己的**私人**远端；不要公开上传作业答案，也不要恢复对官方 `origin` 的 push。

安装器刻意不提供自动更新和自动删除。升级 commit 必须重新审计问题清单、测试、许可证和资源要求；删除前则应由用户确认目标路径及答案备份，避免工具误删学习记录。

## 两种训练模式不得混用

| 模式 | 代码位置 | AI 上限 | 测试证明什么 | 是否改变当前任务 |
|---|---|---|---|---|
| 原生任务 | 私人 workspace 的 `src/` | 由本项目 H0–H5 规则控制 | 本项目任务契约的一部分 | 只由 learner ledger 改变 |
| 官方 assignment | `.external/` 的独立 checkout | Stanford policy 优先，本 pack 最高 H2 | 与固定上游接口/测试兼容 | 仅安装不改变；正式实现一个 problem group 时，它必须成为私人 ledger 的唯一当前任务 |

对 CS336 assignment，AI 可以解释高层概念、帮助定位错误类别或指向低层 API 文档；不得生成代码、伪代码、步骤化解法，不得补 TODO、编辑 checkout 或替用户运行命令。即便学习者不是 Stanford 在读学生，本项目仍使用这一上限保护独立训练证据。

若希望 AI 演示相同概念，应另建本项目原创、不同接口和不同测试的 clean-room native 变式；不得把官方 TODO 当作演示题。

## Assignment 与实际 Task 的边界

`EXT-CS336-A1` 至 `EXT-CS336-A5` 是聚合清单与总 Gate，不是五个可以同时推进的巨型 Task。机器生成导航为每个 problem group 给出唯一 canonical ID，例如 `EXT-CS336-A1-tokenizer-core`。正式实现时只允许选择其中一个 ID，并在私人 learner ledger 中把它登记为唯一 `CURRENT_TASK`；原生主任务同时暂停。安装 checkout、阅读 Task Card 或预习公式都不会自动改变状态，也不会自动解锁后续 assignment。

不要手写或覆盖 ledger。当前五份 assignment 的 `integration_status` 都是 `inventory-audited`：可以安装、检查与 Preview，但在原生 readiness 变成受校验任务映射前 fail closed，不允许登记为 Implementation Lane。预览命令会以非零退出码明确报告这一阻塞：

```bash
python scripts/select_current_task.py EXT-CS336-A1-tokenizer-core
```

选择器不会安装或执行第三方代码，也不会生成 `implemented`、review 或 retention 证据。后续课程批次必须先把 `native_readiness` 与 group 内依赖映射到 catalog 中受验证的具体任务，再把 assignment 升级为 `implementation-ready`；在此之前不存在一键“等价前置”豁免。升级后，若当前任务尚未 `reviewed`，选择器仍默认拒绝切换；暂停旧任务不会把它判为通过。

外部 manifest 的 `integration_status=inventory-audited` 只表示固定版本的 inventory 已审计，不表示 checkout 已安装、当前机器满足资源要求、学习者已具备前置、canonical task 已解锁或任务已经掌握。当前状态只允许 Preview；不得手工绕过选择器。

## 本项目增加的训练证据

上游 pytest 全绿只记为 `implemented` 候选证据。每份 companion Task Card 还要求：

- 前置 Gate 与资源 Gate；
- problem group 级的实现、实验或分析证据；
- shape、数值稳定性、复杂度和系统权衡口述；
- D+2 闭卷复写或缩小版 clean-room 重建；
- D+7 接口、数据或约束变化后的迁移；
- 帮助等级记录和失败复盘。

只有这些证据都满足，才可在私人 ledger 中按本项目状态机推进。外部 manifest 和安装器从不直接写 `state/`；只有选择器在明确应用后写入必要的注册事件与当前快照。problem group 不能与原生 Implementation Lane 并行实施。

learner ledger 中 canonical task 的状态**只描述 companion runtime**。official runtime 的真实 GPU、服务或完整数据实验是单独 review 证据；即使 canonical task 为 `mastered`，也不能据此宣称官方 full assignment 完成。assignment 的 portable aggregate 采用确定规则：

- `reviewed` aggregate：全部 `portable-required` groups 分别至少 `reviewed`；
- `retained_7d` aggregate：全部 `portable-required` groups 分别至少 `retained_7d`；
- `mastered` aggregate：全部 `portable-required` groups 分别为 `mastered`；
- `portable-elective`、`official-only` 与 `optional-capstone` 不阻塞 portable aggregate，但它们未运行时必须明确标为 `not_run`，不能从 aggregate 推断完成。

v0.1 不把 assignment aggregate 伪装成额外 ledger Task；工具按上述规则从 canonical group 快照派生前置判断。这样不会把 portable 与 official 两种完成度压进同一个含糊状态。

## 资源分层

manifest 为每个命令登记 runtime tier，并区分：本地 CPU、单卡 CUDA、多卡/高算力、远端服务或人工审阅。资源层和 problem group 都使用显式 `completion_role`，不能用 CPU 命令或 skip 证明 CUDA/远端实验完成：

| 角色 | 含义 |
|---|---|
| `portable-required` | 公共 companion 最低闭环，必须有可移植证据 |
| `portable-elective` | 可移植选修，不阻塞最低闭环 |
| `official-only` | 官方完整作业范围；只有对应资源可用并真实运行时才能声明完成 |
| `official-full` | runtime tier 属于官方完整路径，不是公共最低 Gate |
| `optional` / `optional-capstone` | 高成本或扩展实验；未运行必须明确写 `not_run` |

- CPU 合同优先验证接口与小规模正确性；
- GPU、分布式、大语料和远端评测必须先确认配额、费用与隐私；
- 未执行的昂贵实验写“未运行/待核实”，不能用代码存在或上游报告替代；
- 不向第三方服务上传公司、客户、个人或未公开数据。

## 维护者升级流程

1. 在临时目录审计新的官方 commit，不在本仓库中直接改 checkout；
2. 对齐 handout problem、adapter、测试节点和运行命令；
3. 递归检查固定 tree 的许可证文件并登记审计方法，不沿用旧结论，也不把“未发现”解释为授权；
4. 更新 `references/registry.json` 与 manifest 的固定证据；
5. 运行 `python scripts/validate_external_courses.py --write-navigation`；
6. 运行基础设施测试和完整离线 CI；
7. 在 PR 中列出新增、删除和重命名的上游项目，并说明学术诚信影响。

机器可读清单见[外部课程导航](../curriculum/external/NAVIGATION.md)，来源事实见[参考登记](../references/registry.json)。
