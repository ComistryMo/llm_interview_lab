import torch


def merge_heads(head_states: torch.Tensor) -> torch.Tensor:
    """Merge (B, heads, S, D) into contiguous (B, S, heads * D)."""
    raise NotImplementedError
