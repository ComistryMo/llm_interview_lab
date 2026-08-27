import torch


def last_true_token(hidden_states: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    """Gather the greatest true mask position in each sequence."""
    raise NotImplementedError
