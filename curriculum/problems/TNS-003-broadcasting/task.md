# TNS-003 — Broadcasting

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def broadcast_add_bias(x: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
```

## Tensor contract

- `x` has shape `(batch, sequence, hidden)` and `bias` has shape `(hidden,)`.
- Both tensors must share dtype and device; invalid rank or size raises `ValueError`.
- Return `x + bias` through broadcasting without Python loops or explicit expansion copies.
- Preserve autograd connectivity and never mutate either input.

## Acceptance

Run `llm-lab test TNS-003 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

