# 大模型算法面试训练路线

这是一份依赖路线，不是固定日历。学习者应根据档案和周投入调整节奏，但不能跳过 Gate。

## 路线原则

- Python 语法附着在真实任务上，不连续安排纯语法周；
- Implementation Lane 同时只有一个主任务；
- Preview Lane 领先 2–4 周，只学公式、shape、I/O 与官方资料；
- 先手写最小版本，再跟框架调用链；
- 每个实现都经历 review、D+2、D+7 和综合迁移；
- 项目经验只作为公开安全语境，简历词汇不等于掌握。

## 能力依赖

```text
真实小任务中的 Python
  → Tensor / shape / mask / autograd
  → stable softmax / logsumexp / cross entropy
  → SGD / Momentum / AdamW
  → training loop / scheduler / checkpoint
  → RMSNorm / attention / RoPE / KV cache
  → VLM processor / projector / collator
  → LoRA / SFT / sequence logprob
  → DPO / reward model
  → PPO / GAE / GRPO
  → Agent loop / trajectory / evaluator
  → Transformers / PEFT / TRL / selected framework call chains
```

算法恢复作为并行维护通道，从数组哈希、双指针和二分逐步到 heap、树图、DP、LRU；利用已有竞赛经验恢复面试表达与 Python 熟练度，不以题量为目标。

## Gate 0：任务驱动 Python

产物包括困难样本筛选、统计、JSONL、异常、类与 pytest。Gate 要求：能闭卷写清晰函数和至少一个类；能解释引用、输入突变、异常和复杂度；D+7 变式通过。

## Gate 1：Tensor、Loss 与 Optimizer

产物包括 shape/mask 小任务、stable softmax、cross entropy、finite-difference gradient check、SGD、Momentum、AdamW 和最小 checkpoint。Gate 要求：结果与 PyTorch 对齐；解释 reduction、稳定性、state dict 和梯度流；完成一次限时综合训练循环。

## Gate 2：Transformer 与 VLM 数据流

产物包括 RMSNorm、causal attention、RoPE、KV cache、LoRA 和 multimodal collator。Gate 要求：逐层写 shape；处理 dtype/device/mask；与公开参考实现对齐；能定位一个错误 mask 或 cache 实现。

## Gate 3：后训练

产物包括 sequence logprob、SFT、DPO、Reward Model、GAE、PPO/GRPO 最小核心和 rollout 数据流。Gate 要求：写公式与张量维度；覆盖 invalid completion、零 reward variance 和 KL/entropy 边界；能解释稳定性与 reward hacking。

## Gate 4：Agent 与源码

产物包括 schema 校验、tool loop、retry/timeout/max steps、trajectory/replay/evaluator，以及一个框架调用链和最小实验。Gate 要求：环境可复现；parser 和 invalid action 有测试；先有对应手写实现再读源码。

## 优先级

P0 是 Python/Tensor/Loss/Optimizer/训练循环/Attention/SFT-DPO/Agent loop 的核心链；P1 是 VLM 深化、RL、源码调用链与项目连续追问；P2 是 MoE、量化、分布式设计和性能原理。FlashAttention CUDA、完整训练框架和多个框架同时深读在前置 Gate 未通过前暂缓。

核心手撕清单见 [curriculum/CORE_40.md](../curriculum/CORE_40.md)，当前唯一任务见 [state/CURRENT_TASK.md](../state/CURRENT_TASK.md)。
