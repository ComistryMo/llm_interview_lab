import torch


def attention_with_probabilities(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    num_heads: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return concatenated attention output and per-head probabilities."""
    raise NotImplementedError
