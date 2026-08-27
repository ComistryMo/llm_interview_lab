import torch


def masked_sequence_classification_loss(
    hidden_states: torch.Tensor,
    attention_mask: torch.Tensor,
    classifier_weight: torch.Tensor,
    classifier_bias: torch.Tensor,
    targets: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return logits, stable mean cross entropy, and class predictions."""
    raise NotImplementedError
