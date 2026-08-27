import torch


def adam_step(
    parameters: list[torch.Tensor],
    states: list[dict[str, object] | None],
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> list[dict[str, object]]:
    """Apply one Adam step and return fresh detached state."""
    raise NotImplementedError

