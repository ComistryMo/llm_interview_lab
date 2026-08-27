# LOSS-008 — LogSumExp

## Goal

Implement the loss from primitive tensor operations with an explicit numerical-stability argument.

## Interface

```python
def stable_logsumexp(logits: torch.Tensor, dim: int = -1, keepdim: bool = False) -> torch.Tensor:
```

## Contract

- Require a non-empty floating tensor, valid `dim`, and exact bool `keepdim`.
- Use the max-shift identity; do not call `torch.logsumexp`.
- Match PyTorch output shape for both `keepdim` values and preserve dtype/device/gradients.
- Remain finite for large finite logits and never mutate the input.

## Forbidden APIs

- `torch.logsumexp`

## Acceptance

Run `llm-lab test LOSS-008 --profile <id>`. Public tests compare values and gradients with a framework reference while exercising extremes, reductions, invalid contracts, and non-mutation.

## Oral defense

Derive the stable formula, state reduction semantics and shapes, explain the backward signal, and give time/space complexity.

