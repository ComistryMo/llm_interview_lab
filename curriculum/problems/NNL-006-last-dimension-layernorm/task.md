# NNL-006 · LayerNorm 与 RMSNorm

资料映射：AI05。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-008](../NNL-008-rmsnorm/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def layer_norm(x, gamma, beta, eps=1e-5): ...
```

## 题目要求

- X[B,T,D]，gamma/beta[D]，eps>0。沿 D 做 LayerNorm，方差分母是 D 而不是 D−1
- 输出与输入 shape/dtype/device 一致，保持 X、gamma、beta 梯度。半精度统计升 float32，float64 保留。禁止 LayerNorm/RMSNorm 库调用。D=1 和常量行输出 beta。O(BTD)。RMSNorm 的独立实现入口为已存在 NNL-008
- 复盘比较两者是否减均值及 Pre/Post-Norm 的残差位置。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 常量输入在 LayerNorm 与 RMSNorm 中为何不同？
- 为什么 D=1 仍需要有定义的行为？
- 方差分母与 eps 不同时还可以直接比较框架结果吗？
- Pre-Norm 与 Post-Norm 改变了哪条残差路径？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/stable/generated/torch.nn.LayerNorm.html)
- [技术定义 2](https://arxiv.org/abs/1910.07467)
