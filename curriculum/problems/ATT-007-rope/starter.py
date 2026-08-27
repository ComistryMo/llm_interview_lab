import torch


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Rotate adjacent feature pairs with precomputed cosine and sine."""
    raise NotImplementedError

