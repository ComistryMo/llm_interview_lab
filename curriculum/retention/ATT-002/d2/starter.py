import torch


def length_masked_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    key_lengths: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Attend from ``(B, Q, D)`` queries to each sample's valid key prefix.

    ``key`` and ``value`` have shape ``(B, K, D/Dv)`` and ``key_lengths``
    has shape ``(B,)``.  Every length must be an integer in ``[1, K]``.
    Return output ``(B, Q, Dv)`` and probabilities ``(B, Q, K)`` without
    modifying any input.
    """
    raise NotImplementedError
