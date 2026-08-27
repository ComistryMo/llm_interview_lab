import torch


def clipped_sgd_step(
    parameters: list[torch.Tensor],
    lr: float,
    max_norm: float,
) -> float:
    """Clip the joint gradient norm for one SGD step and return the pre-clip norm."""
    raise NotImplementedError
