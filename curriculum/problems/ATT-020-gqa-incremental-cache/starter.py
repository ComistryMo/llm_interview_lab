"""GQA 与 KV cache：增量解码一致性：从公开契约独立实现。"""

import torch


def cached_gqa(query, key, value, cache=None):
    raise NotImplementedError("请完成实现")
