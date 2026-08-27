# LOSS-014 — Cross Entropy

## Goal

Implement the loss from primitive tensor operations with an explicit numerical-stability argument.

## Interface

```python
def cross_entropy(logits: torch.Tensor, targets: torch.Tensor, reduction: str = "mean", ignore_index: int = -100) -> torch.Tensor:
```

## Contract

- `logits` is non-empty floating `(batch, classes)` with at least two classes; `targets` is long `(batch,)` on the same device.
- Targets are valid class indices or equal to strict-int `ignore_index`; use stable LogSumExp plus gather.
- Support `none`, `sum`, and `mean`; ignored rows contribute zero, and all-ignored mean is a differentiable zero.
- Do not call framework cross-entropy/log-softmax helpers; preserve dtype/device/gradients and inputs.

## Forbidden APIs

- `torch.nn.functional.cross_entropy`
- `torch.nn.CrossEntropyLoss`
- `torch.log_softmax`
- `torch.nn.functional.log_softmax`

## Acceptance

Run `llm-lab test LOSS-014 --profile <id>`. Public tests compare values and gradients with a framework reference while exercising extremes, reductions, invalid contracts, and non-mutation.

## Oral defense

Derive the stable formula, state reduction semantics and shapes, explain the backward signal, and give time/space complexity.

