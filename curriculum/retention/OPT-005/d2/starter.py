import torch


def functional_adamw(
    parameter: torch.Tensor,
    gradient: torch.Tensor,
    state: dict[str, object] | None,
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
    weight_decay: float = 0.01,
) -> tuple[torch.Tensor, dict[str, object]]:
    """Return a new parameter and state without mutating the inputs."""
    raise NotImplementedError
