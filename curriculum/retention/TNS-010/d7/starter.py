import torch


def causal_sequence_mask(lengths: torch.Tensor, max_length: int) -> torch.Tensor:
    """Return (B, L, L) bool allowed-attention mask for causal valid queries and keys."""
    raise NotImplementedError
