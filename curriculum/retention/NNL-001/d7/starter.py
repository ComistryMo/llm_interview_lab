import torch


class LoadedLinear(torch.nn.Module):
    """A linear module whose registered parameters can be loaded explicitly."""

    def __init__(self, in_features: int, out_features: int, bias: bool = True) -> None:
        super().__init__()
        raise NotImplementedError

    def load_parameters(
        self,
        weight: torch.Tensor,
        bias: torch.Tensor | None = None,
    ) -> None:
        """Copy caller-owned values into this module without aliasing them."""
        raise NotImplementedError

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError
