# NNL-014 · MoE Top-2：dispatch、combine 与梯度路径

资料映射：AI17。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-001](../NNL-001-linear/task.md)、[LOSS-007](../LOSS-007-stable-softmax/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def top2_moe(x, router_logits, experts): ...
```

## 题目要求

- X[N,D]、router_logits[N,E]，E≥2，experts 是 E 个可调用 f_e，输入 [n_e,D] 返回同形。选择两个不同专家，同分取较小 ID
- 仅在两个选中 logits 上 softmax。返回 (output[N,D], indices[N,2], gates[N,2])
- 每 token 两项输出需累加而非覆盖。无 capacity、不丢 token，不是 Switch Top-1。空专家不调用
- 被选 router logits、输入和专家参数须有正确梯度。排序 O(NE log E)，另含专家开销。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么 index_add 比直接赋值更符合 combine 语义？
- top-k 索引不可导，哪些 router 参数仍会得到梯度？
- 没有分配 token 的专家应该如何处理？
- 加入 capacity 后丢弃策略与负载均衡分母如何变化？

## 来源

- [技术定义 1](https://arxiv.org/pdf/2101.03961)
