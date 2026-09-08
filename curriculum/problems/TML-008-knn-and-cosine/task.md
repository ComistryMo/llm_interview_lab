# TML-008 · KNN 分类与余弦近邻检索

资料映射：AI28。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def knn_predict(x, labels, queries, k=1, metric="euclidean"): ...
```

## 题目要求

- X[N,D]、整数 labels[N]、queries[M,D]，1≤k≤N。输出预测标签[M]。metric 可为 euclidean（平方欧氏）或 cosine
- 余弦模式拒绝任意零向量。邻居等距按训练原下标
- 票数同分选较小类标。允许查询空 batch，禁止现成 KNN。O(MND+MN log N)，可逐查询避免保存全矩阵。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 等距邻居与票数同分各用什么规则？
- 零向量的余弦相似度应如何处理？
- 分块距离计算降低的是时间还是峰值存储？
- 近似索引的召回率如何验证？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/neighbors.html)
