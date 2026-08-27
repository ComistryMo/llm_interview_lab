import torch


def masked_mean_embedding(
    weight: torch.Tensor,
    input_ids: torch.Tensor,
    valid_mask: torch.Tensor,
) -> torch.Tensor:
    """Mean-pool embedding rows selected by a [batch, tokens] boolean mask."""
    raise NotImplementedError
