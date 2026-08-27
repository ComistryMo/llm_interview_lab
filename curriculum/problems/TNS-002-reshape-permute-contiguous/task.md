# TNS-002 — Reshape / Permute / Contiguous

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def split_heads(x: torch.Tensor, num_heads: int) -> torch.Tensor:
```

## Tensor contract

- Accept a rank-3 tensor `(batch, sequence, hidden)` and a strict positive integer `num_heads`.
- Require `hidden % num_heads == 0`; violations raise `ValueError`.
- Return a contiguous tensor shaped `(batch, num_heads, sequence, head_dim)` using reshape/permute concepts.
- Preserve dtype, device, values, gradient connectivity, and the input tensor.

## Acceptance

Run `llm-lab test TNS-002 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

