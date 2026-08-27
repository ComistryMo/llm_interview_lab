import torch


def batched_select_rows(
    values: torch.Tensor,
    row_indices: torch.Tensor,
) -> torch.Tensor:
    """Select K rows per batch from (B, rows, H) using long indices (B, K)."""
    raise NotImplementedError
