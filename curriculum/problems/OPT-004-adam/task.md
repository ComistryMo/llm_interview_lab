# OPT-004 — Adam

## Goal

Implement one optimizer update explicitly so parameter mutation and persistent state are auditable.

## Interface

```python
def adam_step(parameters, states, lr, beta1, beta2, eps) -> list[dict[str, object]]:
```

## Contract

- States align with parameters and are `None` or dictionaries containing detached `m`, `v`, and strict positive integer `step`.
- For gradients, update biased moments, increment step, apply bias correction, then update the parameter.
- Skip missing gradients without incrementing their step; return fresh detached state without aliasing caller state.
- Validate all shapes/dtypes/devices and hyperparameter ranges before any mutation; do not call `torch.optim`.

## Constraints

Do not use `torch.optim`. The function may mutate parameters only after full validation; gradients and caller-owned state remain unchanged.

## Acceptance

Run `llm-lab test OPT-004 --profile <id>`. Tests cover closed-form steps, missing gradients, state isolation, validation, and no-grad update semantics.

## Oral defense

Write the update equations, identify every persistent state tensor, explain step timing and bias correction, and distinguish coupled L2 from decoupled weight decay.

