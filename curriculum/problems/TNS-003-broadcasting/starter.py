import torch


def broadcast_add_bias(x: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
    """Add a hidden-dimension bias to a rank-3 tensor."""
    raise NotImplementedError

