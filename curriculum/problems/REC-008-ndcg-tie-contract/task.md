# REC-008 · NDCG@K：排序指标的 gain 与 tie 策略

资料映射：AI35。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def ndcg_at_k(relevance, scores, k): ...
```

## 题目要求

- 单 query 等长 relevance[n]、scores[n]，1≤k≤n
- relevance∈[0,30]。按预测分数降序，同分按原下标
- gain=2**rel−1，位置折扣 log2(rank+1)，rank 从 1 起。返回 DCG/IDCG
- IDCG=0 返回 0，不作 NaN。O(n log n)。禁止现成指标
- 不要与默认线性 gain/并列期望的指标混比。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 指数 gain 与线性 gain 的 NDCG 能直接比较吗？
- 相同预测分数的固定顺序与并列期望有何区别？
- 全零相关性时为何需要显式约定？
- 不同 query 的相关性标注口径怎样影响宏平均？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html)
