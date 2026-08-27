# TNS-011 — Last Valid Token

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def last_valid_token(hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
```

## Tensor contract

- `hidden_states` is `(batch, sequence, hidden)`; `attention_mask` is boolean `(batch, sequence)`.
- Every row must contain at least one valid token; both left and right padding are supported.
- Return `(batch, hidden)` from the greatest valid index in each row.
- Preserve dtype/device/gradient connectivity and do not mutate inputs.

## Acceptance

Run `llm-lab test TNS-011 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

