# NNL-019 · ReLU、Sigmoid 与 SwiGLU 独立激活

资料映射：题目.md 第 32、33、34 项。仅收到题名；嵌入图片未提供，本题固定以下原创训练契约，不声称恢复图片公式。

## 接口

~~~python
def manual_relu(x): ...
def stable_sigmoid(x): ...
def swiglu_activation(gate, up): ...
~~~

## 题目要求

- 三个函数都需实现。manual_relu(x)=max(x,0)，规定 x=0 处导数为 0；stable_sigmoid(x)=1/(1+exp(-x))，包括 x=0 处导数 1/4。
- swiglu_activation(gate,up)=gate*sigmoid(gate)*up；gate/up 形状必须完全相同，否则 ValueError。没有线性投影、参数或输出投影，与 NNL-005 的完整 SwiGLU MLP 区分。
- 支持标量、空张量、非连续视图和绝对值到 1000 的有限浮点输入；Sigmoid 输出及反向梯度须有限，不能仅用 nan_to_num 修补已产生的错误梯度。
- 允许 where、exp 和基础算术；禁止 torch.sigmoid、Tensor.sigmoid、torch.relu、Tensor.relu、nn/F 的 Sigmoid/ReLU/SiLU/GLU 及等价整激活 API。允许借助 autograd 传播基础算子图。
- 每函数 O(numel) 时间和输出存储。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- Sigmoid 的稳定前向为何仍可能有不稳定反向？
- ReLU 在零点不可导时，框架需要固定什么约定？
- SwiGLU 的 gate 与 up 可以任意交换吗？
- 激活函数与完整 MLP 的参数、维度与输出投影有什么区别？

## 来源

- [PyTorch Sigmoid 定义](https://docs.pytorch.org/docs/2.12/generated/torch.nn.Sigmoid.html)
- [PyTorch ReLU 定义](https://docs.pytorch.org/docs/2.12/generated/torch.nn.ReLU.html)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
