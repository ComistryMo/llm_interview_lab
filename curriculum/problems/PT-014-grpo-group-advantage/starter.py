import torch


def grpo_group_advantage(rewards: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Normalize rewards independently inside each prompt group."""
    raise NotImplementedError

