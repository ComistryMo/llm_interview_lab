"""GRPO：组内优势、ratio 与 clipping：从公开契约独立实现。"""

import torch


def grpo_outcome_loss(
    rewards, new_logp, old_logp, ref_logp, mask, clip_eps=0.2, beta=0.0, eps=1e-8
):
    raise NotImplementedError("请完成实现")
