# LOSS-016 · Softmax 前向与反向：不构造 Jacobian

资料映射：AI21。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def softmax_backward(x, upstream): ...
```

## 题目要求

- X[B,D]、upstream[B,D] 为非空 float64，沿最后一维计算 softmax 和向量—Jacobian 乘积。返回 (probabilities, dx)，都与 X 同 shape。不构造 [B,D,D] Jacobian，不调用 autograd。前后向 O(BD)。例 X=[[1000,1000]], upstream=[[1,0]] → P=[[0.5,0.5]], dX=[[0.25,-0.25]]。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 怎样用向量—Jacobian 乘积避免构造三维 Jacobian？
- 为什么梯度每行之和接近零？
- P-onehot 适用于任意上游损失吗？
- 加均值 CE 后 batch 分母应出现几次？

## 来源

- [技术定义 1](https://cs231n.github.io/linear-classify/)
