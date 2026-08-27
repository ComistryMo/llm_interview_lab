import torch


def grpo_clipped_loss(
    logprobs: torch.Tensor,
    old_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    mask: torch.Tensor,
    clip_eps: float,
) -> torch.Tensor:
    """Return the token-masked clipped GRPO policy loss."""
    raise NotImplementedError

