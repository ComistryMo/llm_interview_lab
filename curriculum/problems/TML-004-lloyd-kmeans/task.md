# TML-004 · K-means：确定初始化与空簇策略

资料映射：AI13。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def kmeans(x, centers, max_iter=100, tol=1e-8): ...
```

## 题目要求

- X[N,D]、给定 centers[K,D]，1≤K≤N，max_iter≥1，tol≥0。返回 (labels[N], centers[K,D], inertia)。距离采用平方欧氏距离，同分取较小簇 ID
- 空簇保留旧中心。每轮分配后更新非空簇均值
- 最大中心位移≤tol 或达到上限时停止。必须用最终中心重算标签和 inertia。允许基本 NumPy，禁止 sklearn。时间 O(I N K D)，距离矩阵空间 O(NK)。例：[0,2,10,12]、初始中心 [0,10] → [1,11]，inertia=4。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 空簇保留旧中心与重定位是同一算法吗？
- 为什么返回前要用最终中心重分配标签？
- 距离展开公式何时可能出现微小负数？
- 相同 seed 是否足以保证不同库得到同样聚类？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/clustering.html#k-means)
