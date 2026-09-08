"""PPO loss：策略、价值、熵分别实现：从公开契约独立实现。"""

import torch


def ppo_loss(
    new_logp,
    old_logp,
    advantage,
    value,
    target_return,
    logits,
    mask,
    clip_eps=0.2,
    value_coef=0.5,
    entropy_coef=0.01,
):
    raise NotImplementedError("请完成实现")
