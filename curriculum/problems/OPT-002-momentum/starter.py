import torch


def momentum_step(
    parameters: list[torch.Tensor],
    velocities: list[torch.Tensor | None],
    lr: float,
    momentum: float,
) -> list[torch.Tensor]:
    """Apply one momentum-SGD step and return detached velocity state."""
    raise NotImplementedError

