import torch


def sgd_step(parameters: list[torch.Tensor], lr: float) -> None:
    """Apply one in-place SGD step to trusted local parameters."""
    raise NotImplementedError

