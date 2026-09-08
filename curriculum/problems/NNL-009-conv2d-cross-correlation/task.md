# NNL-009 · 二维卷积：先写对，再考虑 im2col

资料映射：AI25。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-001](../NNL-001-linear/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def conv2d(x, weight, bias=None, stride=1, padding=0): ...
```

## 题目要求

- X[N,Cin,H,W]、weight[Cout,Cin,Kh,Kw]，可选 bias[Cout]
- 整数 stride≥1、padding≥0，dilation=groups=1。深度学习互相关，不翻转核。输出高 floor((H+2p-Kh)/s)+1，宽同理
- 无合法输出时 ValueError。保持输入与核梯度，不调用 torch conv/Conv2d。可循环/切片
- 时间 O(N Cout Hout Wout Cin Kh Kw)。[[1,2,3],[4,5,6],[7,8,9]] 与全一 2×2 核 → [[12,16],[24,28]]。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 框架卷积为何通常不翻转卷积核？
- stride/padding 改变输出尺寸的边界是什么？
- 重叠窗口反传时输入梯度应累加还是覆盖？
- im2col 用哪些额外空间换取 GEMM？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/2.8/generated/torch.nn.Conv2d.html)
