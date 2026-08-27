import torch


def padding_key_mask(lengths: torch.Tensor, max_length: int) -> torch.Tensor:
    """Return (B, 1, 1, max_length) bool mask; true marks padded key positions."""
    raise NotImplementedError
