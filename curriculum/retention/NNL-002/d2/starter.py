import torch


def lookup_embeddings(
    weight: torch.Tensor,
    input_ids: torch.Tensor,
    padding_idx: int | None = None,
) -> torch.Tensor:
    """Look up rows and mask padding outputs without using embedding APIs."""
    raise NotImplementedError
