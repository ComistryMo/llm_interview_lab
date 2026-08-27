import torch


def named_adam_step(
    parameters: dict[str, torch.Tensor],
    states: dict[str, dict[str, object]],
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> dict[str, dict[str, object]]:
    """Update named parameters in place and return fresh independent Adam state."""
    raise NotImplementedError
