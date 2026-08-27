import torch


def per_example_cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Return one stable cross-entropy loss per batch item."""
    raise NotImplementedError
