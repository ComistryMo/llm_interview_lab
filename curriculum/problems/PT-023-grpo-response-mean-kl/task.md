# PT-023 · GRPO：组内优势、ratio 与 clipping

资料映射：AI09。这是原创训练任务，不代表某公司必考题。

推荐准备：[PT-014](../PT-014-grpo-group-advantage/task.md)、[PT-015](../PT-015-grpo-loss/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def grpo_outcome_loss(rewards, new_logp, old_logp, ref_logp, mask, clip_eps=0.2, beta=0.0, eps=1e-8): ...
```

## 题目要求

- rewards[B,G]，G≥2
- 三组 logp 与 bool mask[B,G,T]。优势为组内 (r-mean)/(总体 std+eps)，detach
- old 和 reference 也 detach。ratio=exp(new-old)，策略取 min(ratio*A,clamp(ratio,1−clip_eps,1+clip_eps)*A)
- k3=exp(ref-new)−(ref-new)−1。返回逐回答有效 token 均值，再对 B,G 平均的 -surrogate+beta*k3，所有回答都须非空。0<clip_eps<1、beta≥0、eps>0
- 拒绝溢出 ratio，不偷偷截断。与 PT-015 全 token 平均是不同目标。O(BGT)，不是完整训练器。

## 共同约定

padding 不进入 ratio/KL 的指数运算，梯度为零；beta=0 时跳过 reference KL 项。指数溢出的拒绝规则只针对实际参与 loss 的有效项。

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 负优势时 ratio 变大，为什么仍取两个 surrogate 的 min？
- 逐回答平均和全 token 平均对长回答的权重有什么影响？
- 全组奖励相同时，有参考惩罚是否仍可能产生梯度？
- 旧策略 rollout 重复更新时，k3 能否无条件称为当前策略 KL 的无偏估计？

## 来源

- [技术定义 1](https://arxiv.org/html/2402.03300v3#S4.SS1)
