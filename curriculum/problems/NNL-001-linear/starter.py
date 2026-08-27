import torch


class ManualLinear(torch.nn.Module):
    """A Linear layer built from explicit Parameters and tensor operations."""

    def __init__(self, in_features: int, out_features: int, bias: bool = True) -> None:
        super().__init__()
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

