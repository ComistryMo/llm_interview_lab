"""Task 00C：最后有效 token 分类头。

这是一个独立教学实现，不代表任何真实业务实现。
实际项目采用哪个 token、怎样 pooling，只能在获授权环境中自行核实。
"""

import torch
from torch import nn


class LastValidTokenClassificationHead(nn.Module):
    """从每个序列的最后一个有效 token 取 hidden state，再进行分类。

    输入：
        hidden_states: [batch_size, seq_len, hidden_size]
        attention_mask: [batch_size, seq_len]，有效 token 为 1，padding 为 0

    输出：
        logits: [batch_size, num_classes]
    """

    def __init__(self, hidden_size: int, num_classes: int) -> None:
        super().__init__()
        if hidden_size <= 0:
            raise ValueError("hidden_size must be positive")
        if num_classes <= 1:
            raise ValueError("num_classes must be greater than 1")

        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """完成 forward。

        要求：
        - 检查输入维度；
        - 检查 batch 和 seq_len 是否一致；
        - 每个样本必须至少有一个有效 token；
        - 同时支持 CPU 和 GPU；
        - 不要使用 Python for 循环遍历 batch。
        """
        raise NotImplementedError("TODO: implement forward")
