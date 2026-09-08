# PT-003 · 稳定交叉熵与有效 token 归约

资料映射：AI01。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-014](../LOSS-014-cross-entropy/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def token_cross_entropy(logits, labels, ignore_index=-100): ...
```

## 题目要求

- logits[B,T,V] 与 int64 labels[B,T] 已完成预测位置对齐，V≥1。返回按非 ignore_index token 平均的标量 CE
- 全忽略时返回与 logits 相连的零。禁止 softmax 后 log、cross_entropy/log_softmax 代算。半精度升 float32
- float64 保留。例 logits=[[[1e20,1e20]]]、label=[[0]] → log(2)，不能因巨大公共偏置丢失结果。改变忽略位置不影响损失或梯度。O(BTV)
- 异常标签、形状不匹配抛 ValueError。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么加一个很大的公共 logit 偏置后，两个相同类别仍应得到 log(2)？
- 全忽略 batch 应如何保留零梯度而不产生 NaN？
- 加类别权重后分母的定义怎样变化？
- label smoothing 怎样排除 ignore token？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)
- [技术定义 2](https://docs.pytorch.org/docs/stable/generated/torch.logsumexp.html)
