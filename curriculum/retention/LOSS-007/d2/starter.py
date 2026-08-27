import torch


def stable_log_softmax(logits: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """Compute log-softmax without calling a fused softmax API."""
    raise NotImplementedError
