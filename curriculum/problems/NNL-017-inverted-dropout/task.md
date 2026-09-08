# NNL-017 · Dropout 的前向、反向与训练模式

资料映射：AI32。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def dropout_forward(x, p, training=True, rng=None): ...
def dropout_backward(upstream, multiplier): ...
```

## 题目要求

- 0≤p<1
- rng 为 np.random.Generator。返回 (output, multiplier)，multiplier 与 X 同 shape，训练时是 keep/(1-p)，推理为全 1。实现 dropout_backward(upstream,multiplier)，只能复用前向 multiplier，不得重采样。p=0 与 eval 恒等
- eval 不消耗随机数。O(N) 时间及保存状态空间。不调用现成 dropout。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 反向为什么不能重新采样 dropout mask？
- inverted dropout 在 eval 阶段还要缩放吗？
- 做梯度检查为何要固定 RNG 状态？
- activation checkpointing 重算应保存哪些随机状态？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/2.8/generated/torch.nn.Dropout.html)
