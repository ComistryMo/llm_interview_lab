# TML-001 · 逻辑回归：稳定 BCE 与一个完整训练 step

资料映射：AI23。这是原创训练任务，不代表某公司必考题。

推荐准备：[LOSS-013](../LOSS-013-bce-with-logits/task.md)、[OPT-001](../OPT-001-sgd/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def logistic_step(x, labels, weight, bias, lr=0.1, l2=0.0): ...
```

## 题目要求

- X[N,D]、labels[N] 为 0/1、weight[D]、bias 标量。输出 (loss,dw,db,new_weight,new_bias)。loss 为平均 BCE 加 l2*||weight||²/2，bias 不正则化
- lr,l2≥0。稳定处理 ±1000 logits，不调用 sklearn
- 梯度基于旧参数。只执行一步，不要求线性可分无正则问题收敛到有限权重。O(ND)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么 sigmoid 后取 log 在极端 logit 下不稳定？
- 正则项为何不包含 bias？
- 无正则的线性可分数据是否一定有有限最优权重？
- 加入样本权重后损失分母如何定义？

## 来源

- [技术定义 1](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression)
