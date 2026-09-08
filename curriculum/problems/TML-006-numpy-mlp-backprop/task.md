# TML-006 · NumPy 手写两层 MLP 的完整反向传播

资料映射：AI22。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-016](../LOSS-016-softmax-manual-backward/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def mlp_loss_grads(x, labels, parameters): ...
```

## 题目要求

- parameters=(W1[D,H], b1[H], W2[H,C], b2[C])
- X[N,D]，labels[N] 为合法整数。网络为线性→ReLU→线性，返回 (平均交叉熵 loss, (dW1,db1,dW2,db2))，ReLU 在 0 导数取 0。禁止 autograd
- 梯度必须基于更新前参数
- 不原地更新。时间 O(NDH+NHC)，缓存 O(NH+NC)。所有 logits 都为 0 时 loss=log(C)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么所有层梯度应使用更新前权重？
- ReLU 在零点做有限差分有什么风险？
- 复制整个 batch 后均值 loss 梯度应如何变化？
- 共享权重在两条路径上使用时梯度如何组合？

## 来源

- [技术定义 1](https://cs231n.github.io/optimization-2/)
