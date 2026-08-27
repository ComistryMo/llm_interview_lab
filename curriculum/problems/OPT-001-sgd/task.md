# OPT-001 — SGD

## Goal

Implement one optimizer update explicitly so parameter mutation and persistent state are auditable.

## Interface

```python
def sgd_step(parameters: list[torch.Tensor], lr: float) -> None:
```

## Contract

- Require a non-empty exact list of floating tensors and a finite positive scalar learning rate.
- For each parameter with a gradient, apply in-place `parameter -= lr * grad` under no-grad semantics; skip `grad is None`.
- Validate gradient shape/device/dtype before any update so invalid input causes no partial step.
- Do not mutate gradient tensors or create a graph through the optimizer update.

## Constraints

Do not use `torch.optim`. The function may mutate parameters only after full validation; gradients and caller-owned state remain unchanged.

## Acceptance

Run `llm-lab test OPT-001 --profile <id>`. Tests cover closed-form steps, missing gradients, state isolation, validation, and no-grad update semantics.

## Oral defense

Write the update equations, identify every persistent state tensor, explain step timing and bias correction, and distinguish coupled L2 from decoupled weight decay.

