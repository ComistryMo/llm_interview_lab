# PT-019 · GSPO：序列比率与裁剪损失

## 任务

在 GRPO 的组内优势与 clipped loss 基础上，手写一个不含 KL 项的 GSPO 序列目标。重点比较“先在序列上合并比率”与“逐 token 裁剪再归约”，不是再写一遍同名 GRPO。

建议先阅读 PT-015 比较 token 目标，但它不是硬解锁条件。本题真正依赖的是 LOSS-008 的稳定 log 运算和 TNS-010 的掩码归约；不要求先完成尚缺复测资产的 GRPO 掌握流程。

## 接口

```python
def gspo_sequence_loss(logprobs, old_logprobs, advantages, mask, clip_eps=0.2):
    """返回负的、按序列等权平均的 clipped surrogate 标量。"""
```

- logprobs / old_logprobs：同形状 (B,G,S)，B,G,S>=1，有限 float32/float64；advantages：(B,G)，同 dtype/device、有限；mask：(B,G,S) bool，同 device。
- 每条序列至少一个有效 token；空序列、形状/dtype/device 不符或非有限输入抛 ValueError。
- clip_eps 为有限实数，0<clip_eps<1，不能是 bool。
- 每条序列的比率为有效 token 的 **log 概率差均值的指数**，不是逐 token 比率的算术平均。
- 先得到每条序列比率，再取原 surrogate 与裁剪 surrogate 的较小值；返回对 B×G 序列等权均值的负数。advantage 可正、负或零。
- old_logprobs 与 advantages 即使带计算图也要在本函数中 detach；只让当前 logprobs 的有效 token 获得梯度。不修改任何输入。
- 为聚焦目标定义，测例的有效 log 概率差绝对值不超过 20；不要求极端指数溢出恢复策略。不包含 KL、reward normalization、rollout 或优化器。

## 示例

B=1、G=2、S=2，所有 token 有效；
两条序列的概率比率均为 1（current 等于 old），advantages=[1,-1]，返回 0。

若同一序列两个 token 的比率为 4 和 1/4，则序列比率为 1，不是 2.125。
另一条较短序列仍与它等权，不能按 token 总数重新加权。

## 验证与复杂度

时间 O(BGS)，额外空间至多 O(BGS)。禁止调用现成 RL trainer / GSPO loss。
运行：`llm-lab test PT-019 --profile <id>`。

## 口述追问

1. 为什么用平均 log 比率，而不是所有 token 比率相乘？
2. 正、负 advantage 在 clip 边界上分别如何影响梯度？
3. 长短序列等权与 token 等权会产生什么不同？
4. 与 PT-015 的 token 归约约定相比，这里改变了什么？两者都不能直接代表一个完整 RL 系统。

## 来源与边界

算法参照 [GSPO 原论文 §4.1](https://arxiv.org/html/2507.18071v2#S4.SS1)，省略 KL；接口、样例与测试原创。只有该目标函数的验证，不宣称复现论文训练收益。D+2/D+7 尚未上线。
