import torch


def masked_softmax(logits: torch.Tensor, mask: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """Return stable probabilities with false positions exactly zero."""
    raise NotImplementedError
