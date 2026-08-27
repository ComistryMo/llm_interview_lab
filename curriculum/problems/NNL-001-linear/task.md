# NNL-001 — Linear Layer

## Goal

Implement a reusable neural-network layer from explicit Parameters and primitive tensor operations.

## Interface

```python
class ManualLinear(torch.nn.Module):
    def __init__(self, in_features: int, out_features: int, bias: bool = True): ...
    def forward(self, x: torch.Tensor) -> torch.Tensor: ...
```

## Contract

- Register `weight` as `(out_features, in_features)` and optional `bias` as `(out_features,)` parameters.
- Initialize weight and bias uniformly in `[-1/sqrt(in_features), +1/sqrt(in_features)]`.
- Accept floating `x` whose last dimension is `in_features`; return the same leading shape plus `out_features`.
- Match `x @ weight.T + bias`, preserve dtype/device/gradients, and do not use `torch.nn.Linear`.

## Acceptance

Run `llm-lab test NNL-001 --profile <id>`. Tests inspect registered parameters, shapes, initialization, values, dtype/device, gradients, invalid inputs, and reference alignment.

## Oral defense

Explain parameter shapes and initialization, derive the forward equation, identify gradient destinations, and state time/space complexity.

