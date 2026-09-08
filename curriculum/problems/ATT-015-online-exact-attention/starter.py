"""流式精确 attention：保存统计量，不保存完整分数矩阵：从公开契约独立实现。"""

import torch


def streaming_attention(query, key, value, block_size=128):
    raise NotImplementedError("请完成实现")
