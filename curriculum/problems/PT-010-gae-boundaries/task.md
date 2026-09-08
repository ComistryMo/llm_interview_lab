# PT-010 · GAE：终止、截断与序列边界

资料映射：AI31。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def gae(reward, value, next_value, terminated, boundary, gamma=0.99, lam=0.95): ...
```

## 题目要求

- reward/value/next_value[T]，terminated/boundary[T] 为 bool。terminated 必须同时是 boundary
- 非空序列最后一步必须 boundary=True。时间截断也是 boundary，但不一定 terminated。返回 (advantage, advantage+value)。TD residual 使用 gamma*(1-terminated)*next_value
- 优势递推用 gamma*lam*(1-boundary) 阻断跨段传播。gamma,lam∈[0,1]
- 空序列返回两个空数组。next_value 来自截断前最终 observation，不是 reset 后新状态。O(T)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- termination 与时间 truncation 对 bootstrap 的影响有何区别？
- 为什么 boundary 应中断优势递推但不一定取消 next value？
- 自动 reset 后的新 observation 能代替 final observation 吗？
- lambda=0 时应该退化成哪个量？

## 来源

- [技术定义 1](https://arxiv.org/abs/1506.02438)
- [技术定义 2](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)
