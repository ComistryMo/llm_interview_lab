# OPT-002 — Momentum

## Goal

Implement one optimizer update explicitly so parameter mutation and persistent state are auditable.

## Interface

```python
def momentum_step(parameters, velocities, lr, momentum) -> list[torch.Tensor]:
```

## Contract

- `parameters` and `velocities` are equal-length non-empty exact lists; each velocity is `None` or matches its parameter.
- Use `v = momentum * v + grad`, then `parameter -= lr * v`; initialize missing velocity with zeros.
- Return detached cloned velocities aligned with parameters; skip `grad is None` without changing parameter or velocity.
- Validate the full step before mutation; require finite positive `lr` and `0 <= momentum < 1`.

## Constraints

Do not use `torch.optim`. The function may mutate parameters only after full validation; gradients and caller-owned state remain unchanged.

## Acceptance

Run `llm-lab test OPT-002 --profile <id>`. Tests cover closed-form steps, missing gradients, state isolation, validation, and no-grad update semantics.

## Oral defense

Write the update equations, identify every persistent state tensor, explain step timing and bias correction, and distinguish coupled L2 from decoupled weight decay.

