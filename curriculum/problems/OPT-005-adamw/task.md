# OPT-005 — AdamW

## Goal

Implement one optimizer update explicitly so parameter mutation and persistent state are auditable.

## Interface

```python
def adamw_step(parameters, states, lr, beta1, beta2, eps, weight_decay) -> list[dict[str, object]]:
```

## Contract

- Use the same moment state and bias correction contract as OPT-004.
- For parameters with gradients, apply decoupled weight decay `parameter *= (1 - lr * weight_decay)` separately from the adaptive update.
- Skip parameters with no gradient, including weight decay and step increment.
- Require finite non-negative weight decay and valid Adam hyperparameters; never add L2 decay into the gradient.

## Constraints

Do not use `torch.optim`. The function may mutate parameters only after full validation; gradients and caller-owned state remain unchanged.

## Acceptance

Run `llm-lab test OPT-005 --profile <id>`. Tests cover closed-form steps, missing gradients, state isolation, validation, and no-grad update semantics.

## Oral defense

Write the update equations, identify every persistent state tensor, explain step timing and bias correction, and distinguish coupled L2 from decoupled weight decay.

