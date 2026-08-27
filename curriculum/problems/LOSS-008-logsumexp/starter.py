import torch


def stable_logsumexp(
    logits: torch.Tensor,
    dim: int = -1,
    keepdim: bool = False,
) -> torch.Tensor:
    """Compute stable log(sum(exp(logits))) along dim."""
    raise NotImplementedError

