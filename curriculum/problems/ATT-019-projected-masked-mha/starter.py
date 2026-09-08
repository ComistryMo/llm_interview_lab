"""多头注意力与复合 mask：从公开契约独立实现。"""

import torch


def projected_mha(query_input, context, wq, wk, wv, wo, num_heads, allowed=None):
    raise NotImplementedError("请完成实现")
