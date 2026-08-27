# LOSS-007 — Stable Softmax

## Goal

Implement the loss from primitive tensor operations with an explicit numerical-stability argument.

## Interface

```python
def stable_softmax(logits: torch.Tensor, dim: int = -1) -> torch.Tensor:
```

## Contract

- Require a non-empty floating-point tensor and a valid dimension.
- Compute Softmax by subtracting the maximum on `dim`; do not call `torch.softmax` or `torch.nn.functional.softmax`.
- Return the same shape/dtype/device, with probabilities summing to one on `dim`.
- Remain finite for very large magnitudes, preserve gradients, and do not mutate logits.

## Forbidden APIs

- `torch.softmax`
- `torch.nn.functional.softmax`

## Acceptance

Run `llm-lab test LOSS-007 --profile <id>`. Public tests compare values and gradients with a framework reference while exercising extremes, reductions, invalid contracts, and non-mutation.

## Oral defense

Derive the stable formula, state reduction semantics and shapes, explain the backward signal, and give time/space complexity.

