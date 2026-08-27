import torch


def multi_head_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    num_heads: int,
    mask: torch.Tensor | None = None,
    causal: bool = False,
) -> torch.Tensor:
    """Attend over pre-projected hidden states with independent heads."""
    raise NotImplementedError

