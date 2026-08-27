# TNS-013 — Autograd / Detach / No-Grad

## Goal

Implement the tensor contract below without using a convenience layer that hides the target operation.

## Interface

```python
def autograd_probe(x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
```

## Tensor contract

- Require a floating-point tensor with `requires_grad=True`.
- Return `output = x.square() + x.detach()` and a detached cloned snapshot equal to `x`.
- The output value includes both branches, but gradients flow only through the squared branch.
- Preserve shape/dtype/device and do not call backward inside the function.

## Acceptance

Run `llm-lab test TNS-013 --profile <id>`. Tests cover shape, dtype, device, numerical values, gradients, invalid inputs, and non-mutation where applicable.

## Oral defense

State every input/output shape, explain the chosen axis or view operation, describe gradient flow, and give time plus auxiliary-space complexity.

