# ATT-011 · temperature、top-k、top-p 的顺序与边界

资料映射：AI07。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-007](../LOSS-007-stable-softmax/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def sample_filtered(logits, k=0, p=1.0, temperature=1.0, generator=None): ...
```

## 题目要求

- logits[B,V] 可含 -inf 禁用 token，每行至少一个有限项，无 NaN/+inf。返回 (token[B], probabilities[B,V])。依次 temperature→top-k→剩余分布 top-p→重归一化采样
- temperature>0，0≤k≤V，k=0 不限
- 0<p≤1。同分按 token ID 小者优先，最多保留 k 个有限项。top-p 保留达到阈值的最小前缀（含跨阈值项），p=1 保留全部剩余项。generator 传给采样
- 不得使用 Transformers warper。例概率 [.5,.3,.2]，p=.6 → [.625,.375,0]。完整排序 O(BV log V)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 先 top-p 再温度缩放与相反顺序等价吗？
- top-p 的跨阈值 token 应留下还是删除？
- p=1 与并列 top-k 的行为如何定义？
- 采样 RNG 怎样保存才能重现后续结果？

## 来源

- [技术定义 1](https://huggingface.co/docs/transformers/en/internal/generation_utils)
