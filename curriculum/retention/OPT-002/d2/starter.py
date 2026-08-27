import torch


def functional_momentum(
    parameter: torch.Tensor,
    gradient: torch.Tensor,
    velocity: torch.Tensor | None,
    lr: float,
    momentum: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return fresh detached parameter and velocity tensors for one momentum step."""
    raise NotImplementedError
