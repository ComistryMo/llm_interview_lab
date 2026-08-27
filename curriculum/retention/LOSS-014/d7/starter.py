import torch


def masked_token_cross_entropy(logits: torch.Tensor, targets: torch.Tensor, loss_mask: torch.Tensor) -> torch.Tensor:
    """Return the mean token loss over true mask positions."""
    raise NotImplementedError
