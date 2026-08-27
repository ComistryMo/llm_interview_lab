import torch


def detached_target_mse(
    predictions: torch.Tensor,
    targets: torch.Tensor,
) -> torch.Tensor:
    """Return mean squared error while treating same-shaped targets as detached constants."""
    raise NotImplementedError
