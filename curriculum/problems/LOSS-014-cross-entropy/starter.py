import torch


def cross_entropy(
    logits: torch.Tensor,
    targets: torch.Tensor,
    reduction: str = "mean",
    ignore_index: int = -100,
) -> torch.Tensor:
    """Compute stable multiclass cross entropy for rank-2 logits."""
    raise NotImplementedError

