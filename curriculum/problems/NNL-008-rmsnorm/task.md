# NNL-008 — RMSNorm

## Goal

Implement a reusable neural-network layer from explicit Parameters and primitive tensor operations.

## Interface

```python
class RMSNorm(torch.nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6): ...
    def forward(self, x: torch.Tensor) -> torch.Tensor: ...
```

## Contract

- Register a learnable scale `(dim,)` initialized to ones and a positive finite `eps`.
- Normalize only the final dimension using `x * rsqrt(mean(x^2) + eps)`, then apply scale.
- Use float32 accumulation for float16/bfloat16 inputs and cast the normalized value back to input dtype.
- Preserve leading shapes/device/gradients; do not use `torch.nn.RMSNorm` or LayerNorm.

## Acceptance

Run `llm-lab test NNL-008 --profile <id>`. Tests inspect registered parameters, shapes, initialization, values, dtype/device, gradients, invalid inputs, and reference alignment.

## Oral defense

Explain parameter shapes and initialization, derive the forward equation, identify gradient destinations, and state time/space complexity.

