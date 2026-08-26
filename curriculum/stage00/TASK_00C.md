# Task 00C：最后有效 Token 分类头

前置条件：Task 00A/B 通过，能够解释基本 Tensor shape。

输入：

- `hidden_states`: `[B, T, H]`；
- `attention_mask`: `[B, T]`。

输出：

- `logits`: `[B, C]`。

要求：

- 选择每个样本最后一个有效 token；
- 不用 Python 循环遍历 batch；
- 检查维度和全 padding；
- 支持 CPU/GPU；
- 梯度能流到被选择 hidden state；
- 区分“整个 last_hidden_state Tensor”和“最后一个 token hidden state”。

该教学实现不代表任何真实业务实现。实际 pooling 只能在获授权环境中自行核实。
