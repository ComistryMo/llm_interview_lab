"""完整 Decoder Block：把组件真正接起来：从公开契约独立实现。"""

import torch


def decoder_block(
    x, weights, num_heads, position_ids, cache=None, eps=1e-5, base=10000.0
):
    raise NotImplementedError("请完成实现")
