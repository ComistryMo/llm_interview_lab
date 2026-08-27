# TNS-006 — Gather Along Last Dimension

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def gather_last_dim(values: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
```

## Tensor contract

- `values` has rank at least 2 and `indices` has the same rank and matching leading dimensions.
- `indices` must be `torch.long`, on the same device, and every value must be in `[0, values.shape[-1])`.
- Gather along the last dimension and return the exact `indices.shape`.
- Preserve values dtype/device/gradients and do not mutate inputs.

## Acceptance

Run `llm-lab test TNS-006 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

