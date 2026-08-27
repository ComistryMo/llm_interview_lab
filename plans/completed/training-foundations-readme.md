# Training Foundations 双 Golden Quest 与 README

## 目标与可观察结果

在不改变 LEAN-V2 核心架构的前提下，使 `Tensor & Stable Loss` 与
`Optimizer & Training Loop` 两条 Quest 可从前置解锁连续推进；十五个必修
Problem 均为 `ready + oracle + D+2/D+7`，两个新 Capstone 为
`ready + oracle`，并以一份可在五分钟内开始训练的 GitHub README 呈现产品。

## 当前事实

- 起点：`v0.2.0-alpha.2` / `9c1729b`，39 ready、18 oracle、12 retention-ready。
- Python 3.11.9；基线测试 148 passed、2 skipped；DAG 与 Workspace doctor 通过。
- 既有接口、Catalog、Workspace、Event、Grader 与 CLI 可以复用。

## 范围与不做内容

- 只补目标节点缺失的 Oracle/Retention、两项 Capstone、Quest DAG/E2E、README。
- 不新增 planned 节点、顶层目录或通用架构抽象；不改 mastery 状态机与公开 CLI。
- 不触碰真实 Profile；维护者 Oracle 只进入 Git-ignored Workspace。
- 不增加 field run，不开发 Web、服务端、数据库、模型客户端或外部课程。

## 里程碑与验证

1. 校正两条 Quest 的 sequence 与硬依赖；补 Tensor/Loss Oracle 与 Retention。
   - 定向：Catalog/DAG、目标 public/retention tests、Oracle validator、Quest E2E。
2. 增加并验证 `CAP-LOSS-001`。
   - 定向：public + private/property Oracle；Capstone 解锁与 reviewed 条件。
3. 补 Neural/Optimizer Oracle 与 Retention；增加并验证 `CAP-TRN-001`。
   - 定向：public + private/property Oracle；训练下降、AdamW 状态与解锁 E2E。
4. 重写 README 并增加轻量契约测试。
   - 定向：链接、CLI、统计、AI policy、Mermaid 与 clean-clone smoke。
5. 全量验证、版本更新、PR、7 个 CI、合并与 prerelease。
   - `python -m pytest -q`、CPU PyTorch、clean clone、Git/Profile 隔离。

## 风险、回退与停止条件

- 修改题目契约或 retention 会使旧 fingerprint 失效；同一批必须重新执行 Oracle。
- 数值题以 float64、官方 PyTorch/闭式参考和梯度对齐交叉验证。
- 每个逻辑批次独立 Commit；可按 Commit 反向 revert。
- 若发现系统性数学错误、必须破坏公开 CLI 或会丢失真实 Profile，立即停止。

## 决策日志

- 2026-08-27：保留中文主 README；技术名与 CLI 使用英文，不建立翻译系统。
- 2026-08-27：Quest sequence 表达推荐顺序，`prerequisites` 只表达硬依赖。
- 2026-08-27：Capstone 复用现有 ProblemNode/Review 生命周期，不新增状态或对象层。

## 当前进度

- [x] 基线确认与功能分支创建。
- [x] Tensor & Stable Loss Quest。
- [x] CAP-LOSS-001。
- [x] Optimizer & Training Loop Quest。
- [x] CAP-TRN-001。
- [x] README 与契约测试。
- [x] 全量与 CPU PyTorch 本地验证；clean-clone、远端 CI 和发布由提交后 Gate 完成。

## 最终复盘

最终 Catalog 为 41 ready、188 planned、32 oracle、23 retention-ready、
0 field runs。十五个必修节点均具有经 public + ignored private/property Oracle
验证的独立 D+2/D+7；两个 Capstone 的 public/private Oracle 分别为 11/3 与
18/3 passed。训练基础与 README 契约 15 passed，CPU PyTorch 定向验证通过，
Repository Health 为 165 passed、2 个 Windows 权限相关 skip，DAG/doctor 与
external pack validator 均通过。发布前仍需在 clean clone 和 7 个远端 CI job
重复验证，只有全绿后才合并并创建 prerelease。
