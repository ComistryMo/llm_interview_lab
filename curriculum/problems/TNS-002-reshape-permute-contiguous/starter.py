import torch


def split_heads(x: torch.Tensor, num_heads: int) -> torch.Tensor:
    """Convert (B, S, H) into contiguous (B, heads, S, head_dim)."""
    raise NotImplementedError

