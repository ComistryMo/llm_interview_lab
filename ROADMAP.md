# Project Roadmap

Roadmap 描述公共项目建设，不代表任何学习者已经解锁相应课程。

## v0.1 alpha — Foundation

- [x] Stage 00 原型与当前任务示例；
- [x] 环境检查、默认健康测试与可选 Torch 依赖；
- [x] 状态模型、ledger 与校验；
- [x] 隐私模板与 fail-closed handoff 导出；
- [x] 公共文档、治理文件与基础 CI；
- [x] 拒绝覆盖、禁用 upstream push 的私人 workspace 生成器；
- [ ] 收集首次跨平台使用反馈。

## v0.1.x — Curriculum discovery and provenance

- [x] 建立依赖轴 × 岗位轴课程导航；
- [x] 为现有 Task 登记公共成熟度、runtime、GPU 策略和精确测试节点；
- [x] 建立固定 revision 的外部参考与许可证边界登记；
- [x] 建立不镜像内容的外部课程包协议，并全量登记 CS336 Spring 2026 五份作业；
- [x] 提供固定版本检出、来源验证、资源分层与 D+2/D+7 companion Task Card；
- [x] 在跨平台 CI 中离线校验依赖 DAG、导航漂移和 reference exposure；
- [ ] 使用公开 issue 收集导航可理解性反馈。

## v0.2 — Starter/workspace split

- 分离只读公共 starter 与个人 workspace；
- 提供路径受限的 upstream 同步与 workspace 迁移工具；
- 验证 private repository 创建路径后再评估 GitHub Template；
- 将 current/regression/locked 测试物理分层。

## v0.3 — Stage 00 curriculum quality

- 完成 Python 任务卡 schema、提示隔离和变式测试；
- 建立 Task PR 质量检查；
- 由至少两名新用户完成冷启动可用性测试。

## Later

Tensor/Autograd、Loss、Optimizer 等课程包只在前一 Gate 的教学与测试基础设施稳定后增量加入。不会一次创建大量空任务，也不会把完整参考答案放进公共学员路径。
