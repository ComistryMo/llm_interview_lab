import torch


def ema_snapshot(
    current: torch.Tensor,
    previous: torch.Tensor,
    decay: float,
) -> torch.Tensor:
    """Return a new detached EMA snapshot: decay * previous + (1 - decay) * current."""
    raise NotImplementedError
