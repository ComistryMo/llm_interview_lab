import torch


def multimodal_sft_loss(
    logits: torch.Tensor,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    assistant_mask: torch.Tensor,
    image_mask: torch.Tensor,
    ignore_index: int = -100,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Build multimodal SFT labels and return the shifted masked CE loss."""
    raise NotImplementedError
