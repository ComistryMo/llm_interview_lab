import torch


def adamw_step(
    parameters: list[torch.Tensor],
    states: list[dict[str, object] | None],
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
    weight_decay: float = 0.01,
) -> list[dict[str, object]]:
    """Apply one decoupled AdamW step and return fresh state."""
    raise NotImplementedError

