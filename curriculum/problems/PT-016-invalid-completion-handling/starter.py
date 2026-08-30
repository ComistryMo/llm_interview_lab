import torch


def normalize_valid_group_rewards(
    rewards: torch.Tensor,
    valid_mask: torch.Tensor,
    eps: float = 1e-6,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Normalize verifier rewards without allowing invalid completions to leak."""
    raise NotImplementedError
