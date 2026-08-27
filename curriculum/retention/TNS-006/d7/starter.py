import torch


def gather_masked_token_values(
    token_values: torch.Tensor,
    token_ids: torch.Tensor,
    valid_mask: torch.Tensor,
) -> torch.Tensor:
    """Gather from (B, T, V) with (B, T) ids and zero positions where mask is false."""
    raise NotImplementedError
