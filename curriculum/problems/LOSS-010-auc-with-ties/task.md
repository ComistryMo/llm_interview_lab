# LOSS-010 · ROC-AUC：同分不能按输入顺序算输赢

资料映射：AI14。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def binary_auc(labels, scores): ...
```

## 题目要求

- 输入一维等长二值 labels、有限 scores，高分代表正类。返回标量 AUC：正例分数高于负例记 1，同分记 0.5。只有一个类别或空输入抛 ValueError
- 时间 O(N log N)，不能在实现中构造 N×N 配对矩阵。例 labels=[0,1]、scores=[0.5,0.5] → 0.5。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 同分为何应算半赢而非按输入顺序判胜负？
- 仅一类标签为何不能自动补成 AUC=0.5？
- batch AUC 平均为什么通常不等于全局 AUC？
- 类别不均衡时还需要查看哪些 PR 指标？

## 来源

- [技术定义 1](https://sklearn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html)
