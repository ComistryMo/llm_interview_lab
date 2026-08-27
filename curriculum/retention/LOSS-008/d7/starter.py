import torch


def masked_logsumexp(
    logits: torch.Tensor,
    mask: torch.Tensor,
    dim: int = -1,
    keepdim: bool = False,
) -> torch.Tensor:
    """Compute stable LogSumExp over true mask entries; reject any all-false reduction slice."""
    raise NotImplementedError
