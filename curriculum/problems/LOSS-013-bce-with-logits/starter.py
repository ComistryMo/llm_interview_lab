import torch


def bce_with_logits(
    logits: torch.Tensor,
    targets: torch.Tensor,
    reduction: str = "mean",
) -> torch.Tensor:
    """Compute numerically stable binary cross entropy from logits."""
    raise NotImplementedError

