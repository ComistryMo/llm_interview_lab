# EXT-CS336-A3：Scaling Companion

## 定位与边界

本卡覆盖 Stanford CS336 Spring 2026 Assignment 3 的两个学生交付项：IsoFLOPs scaling-law 拟合，以及受计算预算约束的实验设计与最优配置预测。它不复制官方数据、notebook、API 服务、训练结果、预测数值或答案。

上游仓库中的 pytest 验证 API/dashboard/scheduler 服务，不验证学生的 scaling-law 分析。它们只能算上游基础设施健康证据，不能冒充作业通过。

整份 assignment 是聚合 Gate；`isoflops` 与 `budgeted-search` 是两个独立清单单元。当前 `integration_status=inventory-audited` 只允许 Preview，不写入原生 Workspace。

## 前置 Gate

- `EXT-CS336-A1` 的全部 `portable-required` groups 分别至少 `reviewed`，或有明确登记、可核实的等价原生 LM capstone 路径；
- JSON/实验记录、异常与可复现脚本至少 `retained_7d`；
- Transformer 参数/FLOPs accounting、optimizer/training loop 至少 `reviewed`；
- 能独立推导 log-log power-law 拟合、holdout、外推风险与残差诊断；
- 先通过离线 synthetic sweep 与预算状态机，再考虑真实 GPU 实验。

## 上游作业覆盖

机器清单固定登记 2 个 Problem、0 个 adapter（上游没有学生 adapter）和 7 个上游服务测试节点：

1. `chinchilla_isoflops`：按 compute 档选择观测、拟合 compute-optimal model/data scaling，作图、诊断并外推；
2. `scaling_laws`：在硬预算内规划训练查询，提交可复现方法、配置和预测 loss。

完整迁移的含义是保留这两个交付项和“无 student pytest”的事实，不是把 7 个服务测试写成学生验收。

## 安装与验证

```bash
python scripts/manage_external_course.py show EXT-CS336-A3
python scripts/manage_external_course.py install EXT-CS336-A3 --acknowledge-policy
python scripts/manage_external_course.py status EXT-CS336-A3
python scripts/manage_external_course.py commands EXT-CS336-A3
```

Stanford hosted API 依赖课程网络、学生身份、密钥、队列与 B200 预算。公共用户不得索取、猜测、共享或提交课程凭据；默认使用自己生成的 synthetic runs 或自有 tiny-LM sweep。

## AI 与学术诚信

最高 H2：AI 可解释回归、残差、预算和 API 错误概念，但不能设计提交策略、写分析代码/伪代码、挑选最终配置或计算待提交答案。用户必须自己决定实验并承担预算。

## 证据与验收

- 输入 run schema、单位、过滤规则、重复配置和失败 run 处理有明确契约；
- fit 不只给曲线：必须有 held-out/backtest、残差、outlier/seed 敏感性和外推不确定性；
- 预算 planner 处理 reserve、refund、timeout、duplicate 与 idempotence；
- 真实服务不可用时明确写 `not_run`，用离线替代不能声称完成 Stanford leaderboard；
- 口述回答为何最小 observed loss 不等于可靠 scaling law、外推跨数量级为何危险、compute/data/model 如何共同约束。

## D+2 / D+7

- 复测只针对当前 canonical problem group；`isoflops` 与 `budgeted-search` 分别保留状态，不能互相代替。
- D+2：在新 synthetic dataset 上闭卷重建当前 group 的 reducer/fit/诊断或预算状态机，不看旧图、旧参数或旧决策。
- D+7：为当前 group 加入噪声、缺失 run、异常点、预算取消或外推区间变化，提交新 artifact 与 decision memo。
- 没有 held-out/不确定性或把 API 基础设施测试当学生测试时，不得进入 retention。

## 资源与停止条件

- portable companion：离线 CPU synthetic runs、tiny sweep 记录和图表，完成 `isoflops` group。
- official-full：`budgeted-search` 依赖 Stanford hosted service；仅有正式授权的学生按课程政策使用，本项目不提供密钥、代理或仿冒入口。无权限时保持 `not_run`，不得声称官方 full completion。
- 可选自有实验：用户自有单 GPU sweep，记录真实成本与停止规则，但不能冒充 Stanford 服务结果。
- 若分析依赖未知数据来源、泄露课程答案或用高算力掩盖 fit 诊断不足，立即停止。
