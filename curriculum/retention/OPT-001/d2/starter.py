import torch


def functional_sgd(
    parameter: torch.Tensor,
    gradient: torch.Tensor,
    lr: float,
) -> torch.Tensor:
    """Return one detached SGD update without mutating either input tensor."""
    raise NotImplementedError
