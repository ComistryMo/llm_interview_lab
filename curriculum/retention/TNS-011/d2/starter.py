import torch


def token_at_lengths(hidden_states: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
    """Gather the token at lengths - 1 for each batch row."""
    raise NotImplementedError
