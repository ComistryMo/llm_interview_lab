"""双向 ViT block，遵循题面固定的 mask 和 GELU 约定。"""

import torch


def vit_block(x, weights, num_heads, valid_tokens=None, eps=1e-6):
    raise NotImplementedError("请完成实现")
