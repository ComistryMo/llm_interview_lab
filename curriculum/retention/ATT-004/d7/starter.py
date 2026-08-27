import torch


def causal_padded_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    num_heads: int,
    key_padding_mask: torch.Tensor,
) -> torch.Tensor:
    """Apply causal MHA while excluding false key-padding positions."""
    raise NotImplementedError
