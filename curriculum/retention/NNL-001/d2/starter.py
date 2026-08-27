import torch


def affine_projection(
    x: torch.Tensor,
    weight_io: torch.Tensor,
    bias: torch.Tensor | None = None,
) -> torch.Tensor:
    """Project the final axis using weight stored as [in_features, out_features]."""
    raise NotImplementedError
