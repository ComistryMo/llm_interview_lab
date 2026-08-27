import torch


def scaled_dot_product_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    mask: torch.Tensor | None = None,
    causal: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return attended values and attention probabilities."""
    raise NotImplementedError

