# REC-009 · DIN 局部激活与兴趣聚合

资料映射：AI38。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-001](../NNL-001-linear/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def din_interest(query, history, valid, w1, b1, w2, b2): ...
```

## 题目要求

- query[B,D]、history[B,L,D]、bool valid[B,L]
- 构造 [q,h,q-h,q*h] 顺序的特征 [B,L,4D]，打分 MLP 固定 Linear(4D,U)→ReLU→Linear(U,1)，w1[U,4D],b1[U],w2[1,U],b2[1]。无 softmax，权重允许为负。返回 (interest[B,D], masked_weights[B,L])，interest 为有效历史加权和
- 全 padding 为零。输入、打分网络保留梯度。O(BLDU)，禁止现成 DIN。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么 DIN 用户表示会随候选发生变化？
- 不作 softmax 的权重能保留什么兴趣强度信息？
- 所有有效权重为 1 时应是求和还是均值？
- padding 与历史顺序置换如何验证？

## 来源

- [技术定义 1](https://arxiv.org/abs/1706.06978)
