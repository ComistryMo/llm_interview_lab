import torch


def decoder_attention_with_padding(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    key_padding_mask: torch.Tensor,
    past_length: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply rectangular causal attention over a padded decoder cache.

    The tensors use ``(B, H, Q/K, D/Dv)``.  Queries represent absolute
    positions ``past_length .. past_length + Q - 1`` and ``K`` must equal
    ``past_length + Q``.  ``key_padding_mask`` is boolean ``(B, K)`` where
    ``True`` means a real key.  Return output and probabilities.
    """
    raise NotImplementedError
