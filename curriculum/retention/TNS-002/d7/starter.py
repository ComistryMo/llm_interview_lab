import torch


def pack_head_features(
    packed: torch.Tensor,
    sequence_length: int,
) -> torch.Tensor:
    """Convert (B, heads, sequence_length * D) into contiguous (B, S, heads * D)."""
    raise NotImplementedError
