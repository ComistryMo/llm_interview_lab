# OPT-003 · Nesterov SGD：一步前瞻更新

## 任务

在已实现 SGD / Momentum 的基础上，手写一个**函数式** Nesterov 更新步骤。优化器不仅是背更新公式：还要说清第一步、状态归属和梯度边界。本题不实现训练器，不更新学习者输入。

## 接口

```python
def nesterov_step(parameter, gradient, velocity, lr, momentum):
    """返回 (新参数, 新速度)，均为独立、无计算图的 Tensor。"""
```

- parameter / gradient：同形状、非空的 float32 或 float64 Tensor；dtype/device 相同，元素有限。
- velocity：None（第一次更新）或与 parameter 同形状、dtype/device 的有限 Tensor。
- lr 为有限正实数；momentum 为有限实数，满足 0 < momentum < 1；bool 不算超参数数值。
- 不修改任何输入，包括其 grad；不让参数更新和持久状态保留计算图。返回 dtype/device 与 parameter 一致。
- 形状、类型、有限性或参数范围不合法时抛出 ValueError。

本题采用无 dampening、无 weight decay 的 PyTorch Nesterov SGD 约定：
第一次速度等于当前梯度；其后先累计动量，再以前瞻方向更新参数。允许基本 Tensor 运算，禁止 torch.optim。
这与在预测参数上重新求梯度不是同一个接口：这里的 gradient 已由调用方给出。

## 示例

parameter=[1.0, -2.0]，gradient=[0.5, -1.0]，velocity=None，lr=0.1，momentum=0.9。
返回新参数 [0.905, -1.81]，新速度 [0.5, -1.0]。原参数保持不变。

## 复杂度与验证

时间 O(N)，额外空间 O(N)。公开测试覆盖第一步、多步、非连续 Tensor、状态独立和错误输入。
运行：`llm-lab test OPT-003 --profile <id>`。

## 口述追问

1. 相同梯度下，第一步为何不同于普通 Momentum？
2. 学习率突然改变时，速度里是否应含学习率？请说明约定。
3. 为什么速度不能与 gradient 共用存储？
4. 如果下一批没有梯度，应由调用者如何处理这一参数？

## 来源与边界

算法依据：[PyTorch SGD](https://docs.pytorch.org/docs/stable/generated/torch.optim.SGD.html)。
题面、接口、样例和测试由本项目原创；不含公开参考答案。D+2/D+7 变式尚未实现，不宣称可完成掌握闭环。
