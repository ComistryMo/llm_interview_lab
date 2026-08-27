import torch


def stable_softmax(logits: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """Compute numerically stable Softmax along dim."""
    raise NotImplementedError

