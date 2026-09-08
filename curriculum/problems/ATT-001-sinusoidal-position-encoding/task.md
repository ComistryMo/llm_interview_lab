# ATT-001 · 正弦位置编码：奇数维与分段位置

资料映射：题目.md 第 31 项。仅收到题名；嵌入图片未提供，本题固定以下原创训练契约，不声称恢复图片公式。

## 接口

~~~python
def sinusoidal_encoding(length, d_model, offset=0, base=10000.0, *, dtype=torch.float32, device=None): ...
~~~

## 题目要求

- 返回 [length,d_model]，第 t 行代表绝对位置 p=offset+t。第 2i 维为 sin(p/base**(2i/d_model))，第 2i+1 维为 cos(p/base**(2i/d_model))。奇数 d_model 保留最后一个 sin 通道。
- length、offset 为非负整数，d_model 为正整数，base 是有限且大于 1 的实数；否则 ValueError。dtype 仅为 torch.float32/float64，否则 ValueError。device=None 遵循 PyTorch 默认设备。
- length=0 返回正确 dtype/device 的 [0,d_model]。不修改全局随机状态，不添加到输入 embedding，不包含可学习参数。
- O(length*d_model) 时间和输出存储；禁止直接调用现成位置编码层。推荐准备：TNS-003 广播；RoPE ATT-021 是另一个位置机制。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 为何频率分母用原始 d_model，而不是偶数通道数？
- 奇数维、零长度和 offset 拼接各能暴露什么错误？
- 固定 sin/cos 与 RoPE 分别作用于哪个对象？
- 长度外推可计算是否等于模型可靠外推？

## 来源

- [Attention Is All You Need，位置编码定义](https://arxiv.org/html/1706.03762v7)
