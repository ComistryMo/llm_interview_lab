"""temperature、top-k、top-p 的顺序与边界：从公开契约独立实现。"""

import torch


def sample_filtered(logits, k=0, p=1.0, temperature=1.0, generator=None):
    raise NotImplementedError("请完成实现")
