# TML-009 · K-means++ 初始化

资料映射：AI37。这是原创训练任务，不代表某公司必考题。

推荐准备：[TML-004](../TML-004-lloyd-kmeans/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def kmeans_plus_plus(x, k, seed=0): ...
```

## 题目要求

- X[N,D]，1≤k≤N。返回中心原下标 int64[k]，互不重复
- 用 np.random.default_rng(seed)。第一点 rng.integers(N) 均匀选择，之后按到最近已选中心的平方距离归一化，用 rng.choice 抽样。距离总和为 0 时取最小未选原下标。允许不同样本有相同坐标
- 不实现 greedy 多候选变体。O(NKD)，辅助空间 O(N)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 按距离和平方距离抽样有什么差异？
- 所有样本坐标相同如何终止且不重复选索引？
- 标准与 greedy k-means++ 是否是同一随机过程？
- 更好的初始化为什么不保证全局最优？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)
