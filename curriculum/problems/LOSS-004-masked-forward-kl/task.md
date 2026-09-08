# LOSS-004 · 带 mask 的 token KL 蒸馏

资料映射：AI10。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-008](../LOSS-008-logsumexp/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def masked_distillation_kl(teacher, student, mask, temperature=1.0): ...
```

## 题目要求

- teacher/student logits[B,T,V] 词表和 token 已对齐，bool mask[B,T]。返回 temperature² * 有效 token 平均 KL(teacher||student)
- teacher 停梯度，student 保持梯度。全 mask 为空时返回与 student 连图的零
- temperature>0。禁止直接用 KLDivLoss 替代归约，允许 log_softmax。float64 保留，其余至少 float32 归约。O(BTV)。不把 batchmean 或反向 KL 当本题目标。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- forward KL 与 reverse KL 对哪个分布取期望？
- KLDivLoss 的 batchmean 为什么未必等于有效 token 均值？
- 温度平方是数学 KL 必需的吗？
- 不同 tokenizer 的 teacher 能否直接做 token KL？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/stable/generated/torch.nn.KLDivLoss.html)
- [技术定义 2](https://arxiv.org/abs/1503.02531)
