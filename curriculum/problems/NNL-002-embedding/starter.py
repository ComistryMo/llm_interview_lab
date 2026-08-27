import torch


class ManualEmbedding(torch.nn.Module):
    """An embedding lookup with explicit padding semantics."""

    def __init__(self, num_embeddings: int, embedding_dim: int, padding_idx: int | None = None) -> None:
        super().__init__()
        raise NotImplementedError

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

