# CAP-LOSS-001 — Masked Sequence Classification Loss

实现 `masked_sequence_classification_loss`，把 Tensor、Mask、Linear 与稳定
Cross Entropy 串成一个序列分类前向过程。不得调用
`torch.nn.functional.cross_entropy` 或 `torch.nn.CrossEntropyLoss`。

## 接口

```python
def masked_sequence_classification_loss(
    hidden_states: torch.Tensor,      # [B, T, H], floating
    attention_mask: torch.Tensor,     # [B, T], strict bool
    classifier_weight: torch.Tensor,  # [C, H], floating
    classifier_bias: torch.Tensor,    # [C], floating
    targets: torch.Tensor,            # [B], torch.long
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]
```

按 batch 中每一行 `attention_mask` 为真的**最大位置**选择 hidden state。这一定义
同时支持左 Padding、右 Padding和有空洞的 Mask。随后计算
`logits = selected @ weight.T + bias`，并用数值稳定的 mean Cross Entropy 返回：

- `logits`：`[B, C]`，与输入 floating dtype/device 一致；
- `loss`：标量 Tensor；
- `predictions`：`[B]`，`torch.long`，为 logits 的最大类别下标。

## 契约与边界

- `B`、`T`、`H` 和 `C` 必须为正，且 `C >= 2`；
- 每个样本至少有一个有效 Token；全 Padding 行抛出 `ValueError`；
- floating 输入必须具有相同 dtype/device；Mask、targets 与 hidden 位于同一 device；
- targets 必须是 `torch.long`，取值在 `[0, C)`；形状或类型错误抛出 `ValueError`；
- 支持 non-contiguous `hidden_states`；不得修改或 detach 任一输入；
- 梯度必须到达被选择的 hidden state、classifier weight 与 bias，未选择位置梯度为零；
- 大幅有限 logits 下 loss 仍应有限。

## 验收口述

1. 为什么用 `length - 1` 无法同时处理左 Padding 与有空洞的 Mask？
2. selected states、weight、logits、targets 与 loss 的 Shape 分别是什么？
3. Cross Entropy 的 max-shift 如何避免指数溢出？
4. 哪些 hidden-state 行获得梯度，为什么 Padding 行不会获得梯度？
