import torch


def multi_query_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    num_heads: int,
    mask: torch.Tensor | None = None,
    causal: bool = False,
) -> torch.Tensor:
    """Apply attention with one shared key/value head."""
    raise NotImplementedError

