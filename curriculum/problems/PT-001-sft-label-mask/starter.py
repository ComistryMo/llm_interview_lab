import torch


def build_sft_labels(
    input_ids: torch.Tensor,
    response_mask: torch.Tensor,
    pad_token_id: int,
    ignore_index: int = -100,
) -> torch.Tensor:
    """Build labels that supervise only non-padding response tokens."""
    raise NotImplementedError

