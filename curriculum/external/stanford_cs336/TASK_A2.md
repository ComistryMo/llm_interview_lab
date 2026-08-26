# EXT-CS336-A2：Systems Companion

## 定位与边界

本卡覆盖 Stanford CS336 Spring 2026 Assignment 2 的 profiling、mixed precision、activation checkpointing、FlashAttention、collectives、DDP、optimizer sharding、FSDP 与 parallelism accounting。它不复制官方代码、测试、benchmark 数值或完整答案。

上游 A2 checkout 内含 A1 staff implementation。该目录是答案泄漏源，只能在学习者自己的 A1 集成 Gate 通过后打开，且不得迁入本仓库 `src/`、测试或提示。

整份 assignment 是聚合 Gate。当前 `integration_status=inventory-audited` 只允许安装与 Preview；待原生 readiness 与 group 依赖机器映射完成并升级为 `implementation-ready` 后，每次才可把一个 `EXT-CS336-A2-<group>` 注册为唯一 `CURRENT_TASK`。安装器无法替学习者证明 A1 Gate，只能通过独立 spoiler 确认阻止误开。

## 前置 Gate

- `EXT-CS336-A1` 的全部 `portable-required` groups 分别至少 `reviewed`，或有明确登记、可核实的等价原生 LM capstone 路径；
- Attention、autograd、AMP、optimizer state 与完整训练 step 至少 `retained_7d`；
- 能解释 GPU memory hierarchy、FLOPs、bandwidth、同步与异步；
- DDP/FSDP 前先通过 CPU process-group、collective 和异常清理小任务；
- Triton/Flash 路线前先有稳定 SDPA 与 online softmax 口述证据。

## 上游作业覆盖

机器清单固定登记 27 个 Problem、8 个 adapter 入口和约 14 个参数化测试 case 对应的 8 个顶层 test node，覆盖：

1. benchmark 计时、Nsight、mixed precision、显存快照与 checkpoint schedule；
2. PyTorch/Triton FlashAttention forward、causal、recompute backward 与性能矩阵；
3. 单机 collectives、naive/flat/overlap DDP；
4. optimizer state sharding、FSDP、full-state reconstruction 与 mixed precision；
5. DP/FSDP/TP/2D parallelism accounting 和可选优化 capstone。

上游测试只能证明少量 correctness；不能证明 warmup/synchronize 正确、真正使用 Triton、communication overlap、及时释放 full weights、峰值显存下降或 benchmark 公平。

## 安装与验证

```bash
python scripts/manage_external_course.py show EXT-CS336-A2
python scripts/manage_external_course.py install EXT-CS336-A2 --acknowledge-policy --acknowledge-spoilers
python scripts/manage_external_course.py status EXT-CS336-A2
python scripts/manage_external_course.py commands EXT-CS336-A2
```

CPU/Gloo contract 与 CUDA/Triton/performance contract 必须分别报告；CUDA 缺失时的 skip 不是 FlashAttention 通过。用户自行执行命令，AI 只审查用户提供的结果与代码。

## AI 与学术诚信

官方 assignment 模式最高 H2。允许解释 profiler、报错、collective 语义和高层算法背景；禁止写 Python/Triton/伪代码、给出分片或 backward 步骤、补 TODO、编辑 checkout 或指向现成实现。A2 内置 staff A1 代码不得成为本仓库 H4/H5 示例。

## 证据与验收

- 官方 CPU distributed correctness 与 CUDA kernel correctness 分开记录；
- benchmark 必须记录 warmup、synchronize、重复次数、均值/离散度、dtype、shape、GPU 和软件版本；
- profiler 证据必须能回答时间花在哪里、显存何时分配/释放、通信是否与计算重叠；
- tied weights、frozen params、unused/None grad、不同 dtype 与多次重复运行有明确结果；
- 能口述 online softmax invariant、Flash IO 优势、DDP 初始化/同步、ZeRO-1、FSDP gather/reduce-scatter 和峰值显存；
- 硬件达不到的项必须写 `not_run`，不能写 `passed`。

## D+2 / D+7

- 复测只针对当前 canonical problem group；kernel、distributed 与 accounting 不能用另一 group 的证据相互替代。
- D+2：在新 toy module 或 measurement fixture 上闭卷重建当前 group 的一项 capability，并解释 shape、同步或失败清理。
- D+7：在当前 group 适用的新 shape、tied/frozen parameter、world size 或测量协议下复测，并回答一项 group-specific 口试。
- `profiling-and-kernels` 的 official 结论需要真实 profiler/硬件证据；任何 companion `mastered` 都只表示对应 portable group，不自动表示官方性能作业完成。

## 资源与停止条件

- portable companion：CPU benchmark harness、数值实验、Gloo DDP/sharding/FSDP toy correctness；只推进标为 `portable-required/elective` 的 group。
- official-full：单 CUDA 的 Triton/profiler/Flash，以及多 GPU collective/FSDP 实验；没有相应资源时写 `not_run`，不阻塞 portable aggregate，但不得声称完成官方 full assignment。
- optional：B200 leaderboard capstone，不是默认求职 Gate。
- 若只能通过复制 staff A1、无法稳定清理 process group、没有公平测量协议或把 skip 当通过，停止并降级到前置任务。
