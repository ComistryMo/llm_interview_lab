# LOSS-017 · 成对 Contrastive Loss：标签方向与 margin

资料映射：题目.md 第 15 项。题名未指定全部数学口径，本题固定以下原创训练契约。

## 接口

~~~python
def pairwise_contrastive(a, b, same, margin=1.0, reduction="mean"): ...
~~~

## 题目要求

- a、b 为同形状 [N,D]，N≥1、D≥1；same 为 bool[N]，True 表示同类/正对。令距离 d=||a-b||₂，每对损失为 0.5*(same*d²+(1-same)*max(margin-d,0)²)。不先做 L2 归一化。
- margin 有限且为正。reduction 可为 none、sum、mean，none 返回 [N]，其它返回标量；mean 只除以 N。错误形状、非 bool 标签、非法 margin/reduction 抛 ValueError。
- 在 d=0 处欧氏 norm 的子梯度定为 0，因此相同向量的负对仍有正损失，但本题梯度为 0。d=margin 处梯度为 0；前向与反向均不得产生 NaN。
- 时间 O(ND)、主要临时存储 O(ND)，禁止直接调用完整现成对比损失。允许基础 norm、clamp 和 autograd。
- 原始题名没有给公式。这里选定 pairwise margin 变体；已有 LOSS-006 的双向 InfoNCE 是另一个可练契约，两者不能当成相同目标。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 同类标签 True 在两个分支分别乘上什么？
- 距离超过 margin 的负对为什么不继续推远？
- 对比损失的 pairwise margin 形式与 InfoNCE 的负样本竞争有何区别？
- 零距离负对处为何需要约定子梯度，这能否自动打破完全塌缩？

## 来源

- [Hadsell、Chopra、LeCun：Dimensionality Reduction by Learning an Invariant Mapping](https://www.cs.toronto.edu/~hinton/csc2535/readings/hadsell-chopra-lecun-06-1.pdf)
