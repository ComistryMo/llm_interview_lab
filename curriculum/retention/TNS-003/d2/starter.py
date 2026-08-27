import torch


def broadcast_affine(
    x: torch.Tensor,
    scale: torch.Tensor,
    shift: torch.Tensor,
) -> torch.Tensor:
    """Apply hidden-wise scale and shift to (B, S, H) using (H,) vectors."""
    raise NotImplementedError
