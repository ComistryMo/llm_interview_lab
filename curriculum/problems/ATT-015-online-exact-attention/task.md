# ATT-015 · 流式精确 attention：保存统计量，不保存完整分数矩阵

资料映射：AI16。这是原创训练任务，不代表某公司必考题。

推荐准备：[ATT-002](../ATT-002-scaled-dot-product-attention/task.md)、[LOSS-007](../LOSS-007-stable-softmax/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def streaming_attention(query, key, value, block_size=128): ...
```

## 题目要求

- 单头 Q[L,D]、K[S,D]、V[S,Dv]，float32/float64，S>0
- block_size≥1。返回 [L,Dv]，与 softmax(QKᵀ/sqrt(D))V 一致。每次最多计算 L×block_size 分数，不创建完整 L×S 矩阵
- 禁止 SDPA、MHA。只要求无 mask 推理 forward，返回不携带 autograd 图
- 不得将其宣称为 FlashAttention GPU kernel。维护在线最大值、分母和加权和，额外 O(LC+LDv)，算术 O(LS(D+Dv))。C=1、C>S、尾块不整除都须一致。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 不同块的 softmax 输出为什么不能直接平均？
- 合并两个分片需要哪些最大值、分母和分子统计？
- 线性额外存储是否代表线性计算复杂度？
- 普通 autograd 逐块保留图为何不等于 FlashAttention 的显存保证？

## 来源

- [技术定义 1](https://arxiv.org/pdf/2205.14135)
