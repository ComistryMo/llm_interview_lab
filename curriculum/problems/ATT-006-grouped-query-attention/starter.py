import torch


def grouped_query_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    num_query_heads: int,
    num_kv_heads: int,
    mask: torch.Tensor | None = None,
    causal: bool = False,
) -> torch.Tensor:
    """Apply grouped-query attention to pre-projected tensors."""
    raise NotImplementedError

