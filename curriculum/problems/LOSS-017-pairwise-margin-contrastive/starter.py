"""成对 margin 对比损失；same=True 表示正对。"""

import torch


def pairwise_contrastive(a, b, same, margin=1.0, reduction="mean"):
    raise NotImplementedError("请完成实现")
