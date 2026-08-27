import torch


def token_sequence_logprobs(
    logits: torch.Tensor,
    token_ids: torch.Tensor,
    mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return masked token log-probabilities and per-sequence sums."""
    raise NotImplementedError

