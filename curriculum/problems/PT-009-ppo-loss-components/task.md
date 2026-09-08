# PT-009 · PPO loss：策略、价值、熵分别实现

资料映射：AI30。这是原创训练任务，不代表某公司必考题。

推荐准备：[PT-002](../PT-002-token-sequence-logprob/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def ppo_loss(new_logp, old_logp, advantage, value, target_return, logits, mask, clip_eps=0.2, value_coef=0.5, entropy_coef=0.01): ...
```

## 题目要求

- 五个标量 token 张量 [B,T]、分类 logits[B,T,V]、bool mask[B,T]。返回 {loss, policy, value, entropy}，均标量 tensor：policy=-有效均值 min(r*A,clamp(r,1-e,1+e)*A)
- value=有效均值 (V-R)²/2（不裁剪）
- entropy=有效均值 -Σp log p
- 只在 mask 为 True 的位置计算目标和梯度。被忽略位置即使有很大的有限 log-prob 差，也不能因先做指数再乘零而污染梯度。
- loss=policy+value_coef*value−entropy_coef*entropy。old_logp、advantage、target_return 停梯度，其余保留。mask 全空抛 ValueError，0<clip_eps<1，系数非负。允许基础 log_softmax，禁止整个 PPO helper。负优势 A=-1,r=1.5,e=.2 时 policy=1.5。O(BTV)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 负优势和大 ratio 的裁剪方向如何手算？
- value MSE 与 value clipping 为何不能混称一种实现？
- 熵奖励与 reference KL 惩罚有什么不同？
- old policy、优势、return 分别为何 detach？

## 来源

- [技术定义 1](https://spinningup.openai.com/en/latest/algorithms/ppo.html)
