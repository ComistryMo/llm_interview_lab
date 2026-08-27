import torch


def stable_logmeanexp(
    logits: torch.Tensor,
    dim: int = -1,
    keepdim: bool = False,
) -> torch.Tensor:
    """Compute log(mean(exp(logits))) stably along a non-empty dimension."""
    raise NotImplementedError
