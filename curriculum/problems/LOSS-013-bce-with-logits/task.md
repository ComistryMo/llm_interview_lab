# LOSS-013 — BCE with Logits

## Goal

Implement the loss from primitive tensor operations with an explicit numerical-stability argument.

## Interface

```python
def bce_with_logits(logits: torch.Tensor, targets: torch.Tensor, reduction: str = "mean") -> torch.Tensor:
```

## Contract

- `logits` and `targets` are non-empty floating tensors with identical shape, dtype, and device; targets lie in `[0,1]`.
- Use a numerically stable logits-space formula; do not call framework BCE helpers.
- Support exactly `none`, `sum`, and `mean` reductions with matching output shapes.
- Preserve gradients and inputs; invalid contracts raise `ValueError`.

## Forbidden APIs

- `torch.nn.functional.binary_cross_entropy_with_logits`
- `torch.nn.BCEWithLogitsLoss`

## Acceptance

Run `llm-lab test LOSS-013 --profile <id>`. Public tests compare values and gradients with a framework reference while exercising extremes, reductions, invalid contracts, and non-mutation.

## Oral defense

Derive the stable formula, state reduction semantics and shapes, explain the backward signal, and give time/space complexity.

