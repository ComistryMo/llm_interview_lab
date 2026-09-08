"""DPO loss：先对齐回答 token，再比较相对偏好：从公开契约独立实现。"""

import torch


def completion_logp(logits, tokens, completion_mask):
    raise NotImplementedError("请完成实现")


def paired_dpo(policy, reference, beta=0.1):
    raise NotImplementedError
