import torch


def sequence_mask(lengths: torch.Tensor, max_length: int | None = None) -> torch.Tensor:
    """Return a boolean valid-token mask from sequence lengths."""
    raise NotImplementedError

