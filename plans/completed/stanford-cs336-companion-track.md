# Stanford CS336 Companion Track ExecPlan

## 1. 目标与可观察结果

把 Stanford CS336 Spring 2026 课程页所链接的五个编程作业完整接入本仓库，但不把第三方作业正文、代码、测试、数据、模型或 PDF 镜像进 Apache-2.0 上游。

完成时应能观察到：

1. Assignment 1–5 均固定到完整 commit SHA，并逐项登记 handout problem、adapter、官方测试、运行环境和人工交付物；
2. 用户可用一个通用脚本把官方仓库检出到 Git 忽略的本地目录；工具只 fetch 精确 SHA，记录不可漂移 base 后创建 `learner-work` 分支，并禁用官方远端 push；
3. A1–A4 的 MIT 许可证证据和 A5 “递归审计固定 tree 未发现 LICENSE/COPYING/NOTICE”被明确区分，绝不把 A5 错标为开源；
4. 官方作业仍使用官方测试；本仓库提供前置 Gate、资源分层、口试、D+2/D+7 和岗位映射，不伪造官方答案或测试；
5. Stanford 在读学生看到醒目的学术诚信边界：官方作业的 AI 帮助上限为其政策允许的低级 API/高层概念帮助（本仓库最高 H2），不能使用 H3–H5 代做；
6. 原生 `curriculum/catalog.json` 与外部课程包 catalog 物理分离；27 个 canonical problem groups 和 18 条 companion 依赖边可独立发现；当前 `inventory-audited` 状态 fail closed，只在未来 readiness 完成机器映射并升级为 `implementation-ready` 后才允许进入 Implementation Lane；
7. CI 离线检查全量覆盖、固定版本、许可证状态、路径安全、生成导航和安装器安全契约；
8. `src/stage00/`、学习者状态和 Task 00A-1 的既有结果不变。

## 2. 当前仓库与上游事实

- 当前唯一 Task 是 00A-1，状态 `needs_revision`、帮助等级 H1；
- 原生 catalog 只有四个 Stage 00 Task，只有 00A-1 是 validated；
- 官方 Spring 2026 课程页共有五个大型 assignment，而不是每节 lecture 一个独立 coding assignment；A1 固定仓库 README 自称 Spring 2025 artifact，本项目保留该差异；
- 本次固定版本：
  - A1 `a158843b20107949f1a8d7df1b05cd33b9166712`；
  - A2 `ca8bc81a59b70516f7ebb2da4808daade877c736`；
  - A3 `03e9372992e913061b9e78b5cfcb62ad8a87de35`；
  - A4 `0555bea66369872d912652debf10b115ca0688c8`；
  - A5 `c2734a26308710949fe13226960a1e8cece94b7e`；
- A1–A4 根目录有 Stanford MIT LICENSE；对 A5 固定 tree 的递归文件名审计未发现 LICENSE、COPYING 或 NOTICE，这不是法律意见或授权；
- 全量 inventory 为 124 个 Problem、52 个 adapter 入口和 105 个测试节点；
- 官方 AI policy 允许高层概念或低级编程文档帮助，禁止 AI 直接实现 assignment；
- A2/A4/A5 的完整实验需要昂贵 GPU、分布式环境、远端服务或大数据，不能伪装成默认 CPU CI 可复现任务。

## 3. 范围与明确不做

### 范围

- 外部课程包 schema、Stanford CS336 manifest 和确定性导航；
- 五张 companion Task Card 与全量 problem/test/adapter 覆盖；
- 固定 SHA 的安装、状态、验证和命令提示工具；
- 许可证、学术诚信、算力层级和与原生训练路线的边界文档；
- 离线基础设施测试、默认 CI/维护命令和来源登记。

### 明确不做

- 不复制或翻译官方 handout、PDF、代码、测试、snapshot、fixture、数据、模型权重或答案；
- 不修改任何 `src/` 文件，不替学习者实现 Task 00A-1 或 CS336 答案；
- 不把外部 assignment 标为本仓库的原创任务，也不暗示 Stanford 背书；
- 不在 CI 联网 clone 或执行第三方代码；
- 不把一次官方 pytest 全绿等同于本仓库 `mastered`；
- 不声称 A2/A4/A5 的 GPU/服务实验能在普通笔记本完成；
- 不为 A5 推定未声明的再分发许可。

## 4. 分阶段里程碑

### M1：固定版本与全量审计

- 交叉核对官方课程页、五个 Git tree、handout problem、adapter 和 tests；
- 建立 coding、experiment、written-analysis、optional 分类；
- 记录 MIT 证据、A5 license-not-found 和官方 AI policy。

### M2：外部课程包契约与工具

- 定义独立 manifest schema，不污染原生 Task catalog；
- 实现离线 validator 和生成导航；
- 实现安全安装、status、verify、commands；
- 默认安装到 `.external/stanford-cs336/`，拒绝覆盖，固定 SHA，禁用 push。
- `install --all` 禁用；A2/A4 需单独确认会暴露 A1 staff material；
- list/show 提供不含本机绝对路径的 JSON，供不同 AI 助手可靠读取。
- `show-group` 提供最小 canonical Task 上下文；任务选择器默认 dry-run，并使用 regular/single-link 路径检查、单写者锁、staged validation 和失败回滚保护 learner state。

### M3：教练差异化层

- 每个 assignment 提供前置 Gate、CPU/GPU 路线、证据、口试、D+2/D+7 和停止条件；
- 将所有 upstream problem 映射到 VLM 后训练、Agent、框架/系统或通用底座价值；
- 明确官方 assignment 模式帮助上限与 native clean-room 模式的区别。
- 把 assignment 拆成 canonical problem-group Task；聚合状态、checkout 状态和学习者掌握状态不得混用。
- 为 group 建立无环 companion DAG，禁止 portable-required 通过 elective/non-portable 隐式扩张最低 Gate；该顺序不冒充 Stanford 官方规则。

### M4：集成、回归与审查

- 将 validator 纳入默认 pytest、CI 与维护文档；
- 用本地临时 Git remote 测试安装器，不依赖 GitHub；
- 动态 current-task runner 只执行受校验的原生 pytest nodes，拒绝自动执行第三方命令；
- 运行全量基础设施、状态、handoff、当前定向测试；
- 做来源、许可证、答案泄漏、跨平台、路径和 `src/` diff 审查。

## 5. 验证命令

```text
python scripts/validate_external_courses.py
python -m pytest tests/infrastructure/test_external_courses.py -q
python -m pytest tests/infrastructure/test_manage_external_course.py -q
python -m pytest -q
python scripts/validate_curriculum.py
python scripts/validate_state.py
python scripts/export_handoff.py --dry-run
python -m pytest tests/stage00/test_task_00a1.py -q
git diff -- src state
```

最后一条定向测试仍预期保留学习者当前红灯；本计划不得用课程迁移掩盖它。

## 6. 风险、回退和停止条件

### 风险

- “完整接入”被误解为拥有第三方内容再分发权；
- A5 无许可证却被整体仓库 Apache-2.0 覆盖；
- external task 被误当作当前已解锁 native task；
- 用户在官方在读作业上使用 AI 代做；
- GPU/远端服务实验被错误承诺为免费、离线或稳定；
- 上游更新后 problem 清单、测试和许可证发生漂移；
- 安装脚本覆盖本地答案或执行未审查的第三方代码。

### 回退

- 全部功能使用独立目录、独立 validator 和独立提交，可整体 revert；
- 安装器永不覆盖现有目录，也不自动运行第三方代码；
- external checkout 位于 `.external/`，不进入 Git；
- 更新版本必须新建审计 diff，不能机械替换 SHA。

### 停止条件

- 必须复制 A5 内容才能实现某项功能；
- 无法证明安装目标、远端 URL 或检出 SHA；
- 需要修改当前学习者答案或状态才能让新基础设施通过；
- 无法把某个昂贵实验的“未运行”与“已通过”明确区分；
- 全量覆盖只能靠制造不可执行的 native 空任务来伪装。

## 7. 决策日志

- 2026-08-26：采用 companion track，不 vendor 官方内容；这是 A5 无许可证和学术诚信约束下唯一能同时做到全量、公开、可维护的方案。
- 2026-08-26：固定 Spring 2026 的五个 HEAD；更新必须重新审计，不跟随 `main` 漂移。
- 2026-08-26：外部官方测试证明 upstream compatibility；本仓库 mastery 仍要求独立口述和 clean-room D+2/D+7 迁移。
- 2026-08-26：官方 assignment 模式遵守 Stanford AI policy，帮助上限为非步骤化概念提示 H2，禁止伪代码、代码片段和完整实现。
- 2026-08-26：A2 与 A4 都包含 A1 staff material，禁用批量安装并增加独立 spoiler acknowledgement。
- 2026-08-26：公共最低闭环、官方完整路径与可选 capstone 使用不同 `completion_role`，CPU skip 不能证明 GPU/远端实验。
- 2026-08-26：五份 assignment 保持 `inventory-audited` / Preview-only；现有原生 catalog 尚不足以机器证明 CS336 readiness，因此不接受布尔自证或手工 ledger 绕过。
- 2026-08-26：canonical learner 状态只证明 companion runtime；official runtime 必须另有真实运行证据，不能从 `mastered` 推定。
- 2026-08-26：安装器拒绝 Git config/env/URL rewrite、replace ref、alternates、grafts、worktree indirection 和多值 remote 等来源身份绕过；不扫描或执行第三方工作树。

## 8. 当前进度

- [x] 读取仓库规则、状态、课程元数据和来源治理；
- [x] M1 固定版本与全量审计；
- [x] M2 外部课程包契约与工具；
- [x] M3 教练差异化层；
- [x] M4 集成、回归与审查；
- [x] 最终复盘并移动到 `plans/completed/`。

## 9. 最终复盘

本计划以 companion track 完成，而不是复制式迁移：五份官方 assignment 的 124 个 Problem、52 个 adapter 入口和 105 个测试节点均被固定版本登记，并拆成 27 个 canonical groups、18 条小步训练依赖；仓库没有加入上游代码、测试体、PDF、fixture、数据、prompt、模型或答案。

固定的五个 SHA 在 2026-08-26 重新执行 `git ls-remote ... HEAD` 后均仍与官方 HEAD 一致。A1–A4 的 MIT 证据与 A5 “固定 tree 未发现许可证文件”的负面审计保持分离；后者不构成法律意见或再分发授权。

最终稳定树验证：

- 默认回归：`174 passed, 3 skipped`；三个 skip 均为当前 Windows 账户缺少 symlink/reparse 创建权限；
- curriculum、external-course 与 learner-state validator 全部通过，生成导航 current；
- handoff dry-run 通过且未创建归档；
- 当前 00A-1 定向测试仍为 `5 passed, 1 failed`，符合 `needs_revision`；
- `git diff -- src state` 与 `git ls-files .external` 均为空；
- 本机 Python 3.9.2 低于公开契约的 Python 3.10+，因此仍需以 CI 的 3.10/3.11/3.12 矩阵作为支持版本证明。

当前外部 pack 的准确能力边界是“全量 inventory、安装、导航、Preview、AI 约束和自动校验完成”，不是“学习者现在已解锁作业”。后续课程批次必须建立具体 native readiness Task 映射，经审查后才能把单个 assignment 升级为 `implementation-ready`。
