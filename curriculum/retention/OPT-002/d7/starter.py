import torch


def named_momentum_step(
    parameters: dict[str, torch.Tensor],
    velocities: dict[str, torch.Tensor],
    lr: float,
    momentum: float,
) -> dict[str, torch.Tensor]:
    """Update named parameters in place and return fresh velocity state."""
    raise NotImplementedError
