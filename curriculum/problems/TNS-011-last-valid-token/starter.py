import torch


def last_valid_token(hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    """Select the greatest valid token position from each sequence."""
    raise NotImplementedError

