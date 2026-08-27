import torch


def train_tiny_sequence_classifier(
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    targets: torch.Tensor,
    *,
    vocab_size: int,
    num_classes: int,
    embedding_dim: int = 8,
    batch_size: int = 2,
    epochs: int = 20,
    lr: float = 0.05,
    weight_decay: float = 0.01,
    seed: int = 0,
    dtype: torch.dtype = torch.float64,
) -> dict[str, object]:
    """Train a deterministic CPU sequence classifier with a manual AdamW step."""
    raise NotImplementedError
