import torch


def add_head_bias(scores: torch.Tensor, head_bias: torch.Tensor) -> torch.Tensor:
    """Add a (heads,) bias to attention scores shaped (B, heads, Q, K)."""
    raise NotImplementedError
