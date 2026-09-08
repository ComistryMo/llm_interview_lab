# NNL-018 · Linear 反向传播：任意前导维度的 VJP

资料映射：题目.md 第 25 项。仅收到题名；嵌入图片未提供，本题固定以下原创训练契约，不声称恢复图片公式。

## 接口

~~~python
def linear_backward(x, weight, grad_output, bias=True): ...
~~~

## 题目要求

- NumPy float64：x[...,I]、weight[O,I]、grad_output[...,O]，前导形状必须完全相同。I、O 为正数；x 可以是一维向量，前导 batch 可以含零长度，允许非连续视图。
- 前向固定为 y=x@weight.T+b；只返回上游 grad_output 对应的 (grad_x,grad_weight,grad_bias)。返回形状依次为 x.shape、weight.shape、[O]；bias=False 时第三项为 None。无需传入或返回 b。
- 参数梯度累加所有前导维度。接口没有 loss mean，不可再除以 batch/token 数。必须手算 VJP，禁止 torch、JAX、autograd、数值差分作为提交算法。
- 维度数量、特征维、上游形状不匹配时 ValueError。空 batch 返回空 grad_x 与零参数梯度。
- 设 K 为前导维度乘积，时间 O(KIO)，除输入外主要存储 O(KI+OI+O)。推荐先做 NNL-001；其 autograd 前向通过不能替代本题手算反向。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 为何 weight 的梯度需归约所有前导轴？
- 什么时候应该平均梯度，为什么此接口不能自行平均？
- 向量、序列、空 batch 如何统一解释？
- 如何用有限差分验证任意上游 VJP，而不只验证 sum(y)？

## 来源

- [PyTorch Linear，权重布局及前向定义](https://docs.pytorch.org/docs/stable/generated/torch.nn.Linear.html)
