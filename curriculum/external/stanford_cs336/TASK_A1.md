# EXT-CS336-A1：Basics Companion

## 定位与边界

本卡接入 Stanford CS336 Spring 2026 课程页所链接 Assignment 1 仓库的完整自学范围：byte-level BPE、tokenizer、Transformer、loss、AdamW、训练循环、生成与消融。固定仓库 README 仍把该 artifact 标为 Spring 2025；本项目明确保留这一年份差异，不把课程链接语境误写成 artifact 自述。它不是官方作业的镜像或翻译，也不包含完整答案；上游 PDF、starter、tests、snapshots、fixtures 和数据只存在于用户显式安装的外部 checkout。

`EXT-CS336-A1` 是大型 capstone，不应替代本仓库从 Python、Tensor、Loss 到 Transformer 的小步任务。它的价值是验证多个已掌握组件能否在一个真实契约中集成。

整份 assignment 只是聚合 Gate，不得作为第二条并行 Implementation Lane。当前 `integration_status=inventory-audited` 只允许安装与 Preview；problem-group ID 仅用于冻结清单和证据边界，不写入原生 Workspace。

## 前置 Gate

- Gate 0 已 `mastered`：函数、类、异常、容器、文件、pytest 与可变对象；
- stable softmax、cross entropy、AdamW、scheduler、gradient clipping 和 checkpoint 至少 `retained_7d`；
- Linear、Embedding、RMSNorm、SwiGLU、RoPE、causal attention 与 Transformer block 至少 `reviewed`；
- 能在不看答案的情况下逐层说明 shape、dtype、device、mask 与梯度；
- 未满足时只允许把 handout 当 Preview，不开始官方实现。

## 上游作业覆盖

机器清单固定登记 38 个 Problem、21 个 adapter 接口和 48 个顶层测试节点，分为：

1. Unicode/bytes、BPE 训练、特殊 token 边界、streaming tokenizer；
2. Linear、Embedding、RMSNorm、SiLU/SwiGLU、RoPE、softmax、SDPA、MHA、Transformer；
3. cross entropy、AdamW、warmup-cosine、global gradient clipping、data loader、checkpoint；
4. 完整训练、temperature/top-p/EOS decoding、日志、学习率与 batch sweep；
5. norm、position encoding、FFN 消融和可选大语料实验。

清单也保留 Unicode 与资源 accounting 等 analysis Problem，避免把“没有 pytest”误判为“不属于作业”。Problem ID、测试节点和接口名只用于兼容审计，不复制实现或测试正文。

## 安装与验证

先查看政策与计划，不会自动执行第三方代码：

```bash
python scripts/manage_external_course.py show EXT-CS336-A1
python scripts/manage_external_course.py install EXT-CS336-A1 --acknowledge-policy
python scripts/manage_external_course.py status EXT-CS336-A1
python scripts/manage_external_course.py commands EXT-CS336-A1
```

安装器检出固定 SHA、创建本地 learner branch、记录 upstream base 并禁用向官方 `origin` push。用户自行审查依赖后，在外部 checkout 中运行官方命令；AI 不代为运行官方 assignment 命令。

## AI 与学术诚信

官方 assignment 模式最高 H2：允许官方 API/错误信息说明、非步骤化高层概念，以及只指出不变量或错误类别的审查；禁止给出可执行修改步骤、伪代码、具体算法步骤、关键片段、TODO 实现、自动编辑与完整答案。即使用户说“允许你直接实现本题”，官方课程政策仍优先，H3–H5 不解锁。

正在修读 Stanford CS336 的学生必须以当前课程政策和 staff 指示为准；本项目不得用于提交、规避 Honor Code 或获取他人答案。

## 证据与验收

只有以下证据同时成立，对应 problem group 才能记为 `reviewed`；整份 assignment 的 portable aggregate 只在全部 `portable-required` group 达标后成立：

- 用户亲自运行固定版本的官方测试并保存命令、环境、exit code 与未运行项；
- 逐条审查文字限制，包括禁止调用的高层实现、初始化、特殊 token、dtype/device、任意 batch 维和输入不突变；
- tokenizer 与训练实验记录数据来源、机器、峰值内存、时间、随机种子和失败运行；
- 能解释至少：BPE tie-break、stable softmax、causal mask、RoPE、pre-norm、AdamW decoupling、warmup/cosine、checkpoint resume；
- 至少完成一次小规模端到端训练、resume 等价性、perplexity 与生成分析；
- 所有外部帮助按实际 H0–H2 记录。

## D+2 / D+7

- 复测只针对当前 canonical problem group；不得用整份 assignment 的混合抽题替代该 group 的独立状态证据。
- D+2：不打开外部 checkout，从当前 group 随机抽取一项 capability，以不同签名和不同 toy fixture 闭卷重建或重新推导。
- D+7：改变当前 group 相关的 vocabulary、shape、数据、状态恢复或失败约束，完成结构变式并口述错误定位；不得复用官方 snapshot。
- assignment 级 retention/mastery 只在全部 `portable-required` groups 分别达到相应状态后聚合，不由一次集成变式直接授予。
- 若发生越权 H3–H5 帮助或查看第三方答案，该次官方实现证据作废；只能用不同接口、输入结构和测试的 clean-room 变式重新建立独立证据。

## 资源与停止条件

- CPU：官方 correctness、toy BPE、tiny training smoke；绝对速度阈值和 Linux 内存测试必须标注平台差异。
- 单 GPU：训练、生成和受控消融；按个人算力缩小模型/数据，但不得伪造官方规模。
- 重算力/leaderboard：可选，不是面试 mastery Gate。
- 若前置原生组件尚未掌握、依赖版本冲突无法隔离、实验数据来源不清或只能靠 staff/第三方答案推进，立即停止并回到唯一原生任务。
