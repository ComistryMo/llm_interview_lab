# TML-007 · PCA：训练集拟合与测试集变换

资料映射：AI27。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def fit_pca(x, k): ...
def transform_pca(x_new, fitted): ...
def inverse_transform_pca(z, fitted): ...
```

## 题目要求

- X[N,D]，N≥2，1≤k≤min(N,D)。允许 np.linalg.svd，禁止现成 PCA。返回 (train_mean[D], components[k,D], variance[k], ratio[k])
- 方差用 N−1 分母，ratio 相对所有奇异值的总方差，常量训练集 ratio 全 0。不白化、不标准化。另实现 transform_pca(x_new,fitted) 与 inverse_transform_pca(z,fitted)，始终复用训练均值。SVD 方向符号可不同，按重建/子空间验收。时间 O(ND min(N,D))。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 测试样本为何必须使用训练均值？
- 主方向符号不同是否意味着结果错误？
- 中心化与特征标准化是什么关系？
- 重根子空间如何比较、白化额外做什么？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
