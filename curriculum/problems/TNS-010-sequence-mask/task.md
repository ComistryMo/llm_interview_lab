# TNS-010 — Sequence Mask

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def sequence_mask(lengths: torch.Tensor, max_length: int | None = None) -> torch.Tensor:
```

## Tensor contract

- `lengths` is a rank-1 `torch.long` tensor of non-negative sequence lengths.
- `max_length` is `None` or a strict non-negative integer and cannot be smaller than the largest length.
- Return a boolean mask `(batch, max_length)` with `True` exactly where position `< length`.
- Preserve device, support empty batches when `max_length` is explicit, and avoid Python loops over examples.

## Acceptance

Run `llm-lab test TNS-010 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

