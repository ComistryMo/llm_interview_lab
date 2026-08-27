import torch


class RMSNorm(torch.nn.Module):
    """Root-mean-square normalization over the final dimension."""

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

