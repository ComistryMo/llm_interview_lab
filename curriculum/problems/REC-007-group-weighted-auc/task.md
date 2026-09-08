# REC-007 · GAUC：先分组，再说明权重口径

资料映射：AI34。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-010](../LOSS-010-auc-with-ties/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def grouped_auc(groups, labels, scores): ...
```

## 题目要求

- groups、labels、scores 是等长一维序列。group ID 可哈希
- labels 为 0/1。仅纳入有正负两类的组
- 每组按同分半赢的 AUC，按组样本数加权。返回 {gauc: float, valid_groups: int, excluded_samples: int}
- 全组无效抛 ValueError，不能返回 0.5。O(Σ n_g log n_g)，禁止 sklearn。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 用户等权、曝光数和样本对数加权分别代表什么？
- 过滤单类组时分母如何变化？
- 为什么组间分数整体平移不改 GAUC 却可改变 AUC？
- 分 batch 计算再平均会丢失什么？

## 来源

- [技术定义 1](https://arxiv.org/pdf/1706.06978)
