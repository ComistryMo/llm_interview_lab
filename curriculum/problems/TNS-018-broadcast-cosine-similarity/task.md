# TNS-018 · 余弦相似度：广播、归约轴与零向量

资料映射：题目.md 第 30 项。题名未指定全部数学口径，本题固定以下原创训练契约。

## 接口

~~~python
def cosine_similarity(a, b, dim=-1, eps=1e-8): ...
~~~

## 题目要求

- a、b 可广播成同一个形状；在共同形状的 dim 轴上计算内积，并除以 max(||a||₂,eps)*max(||b||₂,eps)。归约轴从输出中移除，支持正/负 dim。
- eps 是有限正数。输入至少一维，归约长度为正；不兼容的广播、越界 dim、非法 eps 抛 ValueError。其它轴可以零长度。
- 零向量输出 0。接近零的向量严格采用逐范数截断，不在分母额外加 eps。梯度按上述 clamp 后的数学函数传播，零范数的 norm 子梯度定为 0；不要求与特定框架在低于 eps 时的内部梯度技巧一致。
- 禁止现成 cosine_similarity；允许广播、sum、norm、clamp 等基础运算。设广播后共有 M 个数，时间 O(M)，允许 O(M) 临时存储。
- 本题返回相似度本身；TML-008 的 KNN 是后续应用。原图未提供，不能据题名猜测其它零向量策略。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 先广播后按哪个维度求内积，输出 shape 是什么？
- 分别截断两个范数与截断范数乘积会得到相同值吗？
- 零向量的数值输出、数学定义和梯度如何分别约定？
- 在范数不触发 eps 时，正比例缩放应保留什么不变量？

## 来源

- [PyTorch functional cosine_similarity 的逐范数 eps 定义](https://docs.pytorch.org/docs/2.12/generated/torch.nn.functional.cosine_similarity.html)
