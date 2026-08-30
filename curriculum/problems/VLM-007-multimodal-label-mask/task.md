# VLM-007 — Multimodal SFT Label Mask

## Goal

Implement the label-building and loss contract used by a vision-language SFT
collator.  A batch contains ordinary text tokens, visual placeholder tokens,
padding, and assistant targets.  Only assistant target tokens that are both
attended and non-visual may contribute to the causal-language-model loss.

This is a clean-room exercise.  It intentionally does not depend on a
processor, tokenizer, or model implementation.

## Interface

```python
def multimodal_sft_loss(
    logits: torch.Tensor,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    assistant_mask: torch.Tensor,
    image_mask: torch.Tensor,
    ignore_index: int = -100,
) -> tuple[torch.Tensor, torch.Tensor]:
    ...
```

## Contract

- `logits` has shape `(B, L, V)` and is floating point.  Position `t` is the
  model prediction for token `input_ids[:, t]`; the function performs the
  usual causal shift by dropping logits at the last position and labels at the
  first position.
- `input_ids` has shape `(B, L)`, is a signed integer tensor on the same
  device as `logits`, and is not mutated.  `B > 0`, `L >= 2`, and `V > 0`.
- `attention_mask`, `assistant_mask`, and `image_mask` are boolean `(B, L)`
  tensors on the same device.  A target is valid exactly when
  `attention_mask & assistant_mask & ~image_mask` is true.  Image masking wins
  even if a malformed sample marks an image position as assistant text.
- Return `(loss, labels)`, where `labels` is a fresh `(B, L)` tensor with the
  input IDs at valid positions and `ignore_index` everywhere else.  `loss` is
  the mean cross-entropy over valid *shifted* target positions only, with the
  same floating dtype and device as `logits`.
- Every batch row must retain at least one valid target after the causal shift;
  otherwise raise `ValueError` rather than silently producing a misleading
  zero/NaN loss.  Valid shifted IDs must lie in `[0, V)`; ignored positions
  may contain placeholder IDs outside that range.
- `ignore_index` is a non-boolean Python integer representable by the input
  integer dtype.  Reject mismatched shapes/devices/dtypes, non-finite logits,
  and invalid masks before doing any partial work.
- Preserve gradients through `logits` only.  Masks and IDs are metadata; do
  not mutate any caller-owned tensor.

## Acceptance

Run `llm-lab test VLM-007 --profile <id>`.  Public tests cover numerical
alignment with a transparent reference, causal shift, image/prompt/padding
precedence, per-row empty targets, dtype/device/shape contracts, gradient
flow, non-mutation, and invalid inputs.

## Oral defense

- Draw the `(B, L, V)` to `(B, L-1, V)` and `(B, L)` to `(B, L-1)` shift.
- Explain why visual embeddings and prompt tokens are context but not SFT
  targets, and why an image mask must override an assistant mask.
- Explain how mixed image counts and padding survive collation without
  leaking labels across samples.
- Identify the failure mode if all targets in one row are ignored, and state
  how a production collator would filter or report that sample.
- State which tensors should carry gradients and how the loss reduction
  changes when token counts differ between examples.
