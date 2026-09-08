"""LoRA 线性层与合并一致性：从公开契约独立实现。"""

import torch


def lora_forward(x, weight, bias, a, b, alpha=1.0):
    raise NotImplementedError("请完成实现")


def merge_lora(weight, a, b, alpha=1.0):
    raise NotImplementedError
