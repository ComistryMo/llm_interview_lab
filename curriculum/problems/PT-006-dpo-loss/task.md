# PT-006 — DPO Loss

## Goal

Implement one auditable post-training data or objective primitive.

## Interface

```python
def dpo_loss(policy_chosen, policy_rejected, reference_chosen, reference_rejected, beta) -> tuple[torch.Tensor, torch.Tensor]:
```

## Contract

- All four inputs are finite floating `(batch,)` tensors with identical dtype/device and no required gradients on reference values.
- Compute logits `beta * ((policy_chosen-policy_rejected) - (reference_chosen-reference_rejected))`.
- Return stable per-example `-log(sigmoid(logits))` and scalar reward accuracy `(logits > 0).mean()`.
- Require finite positive `beta`; preserve policy gradients and do not mutate inputs.

## Acceptance

Run `llm-lab test PT-006 --profile <id>`. Tests cover shapes, masks, stable values, gradients, degenerate groups, invalid data, and input immutability.

## Oral defense

Trace data from tokens or rewards to the returned objective, derive the formula, explain masking/reduction, and identify reward-hacking or zero-variance failure modes.

