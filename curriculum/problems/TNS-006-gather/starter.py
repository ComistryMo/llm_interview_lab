import torch


def gather_last_dim(values: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    """Gather values using long indices along the final dimension."""
    raise NotImplementedError

