import torch


def functional_adam(
    parameter: torch.Tensor,
    gradient: torch.Tensor,
    state: dict[str, object] | None,
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> tuple[torch.Tensor, dict[str, object]]:
    """Return one detached Adam parameter update and fresh moment state."""
    raise NotImplementedError
