"""Packing：attention 隔离与监督隔离是两件事：从公开契约独立实现。"""

import torch


def packing_masks(segment_ids, position_ids, supervised):
    raise NotImplementedError("请完成实现")
