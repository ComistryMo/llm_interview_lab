# PT-014 — GRPO Group Advantage

## Goal

Implement one auditable post-training data or objective primitive.

## Interface

```python
def grpo_group_advantage(rewards: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
```

## Contract

- `rewards` is a finite floating `(prompts, completions_per_prompt)` tensor with at least two completions per group.
- Normalize each row with population mean and population standard deviation.
- If a row has zero variance, return exact zeros for that row instead of amplifying numerical noise.
- Return detached advantages with the same shape/dtype/device; require finite positive `eps`.

## Acceptance

Run `llm-lab test PT-014 --profile <id>`. Tests cover shapes, masks, stable values, gradients, degenerate groups, invalid data, and input immutability.

## Oral defense

Trace data from tokens or rewards to the returned objective, derive the formula, explain masking/reduction, and identify reward-hacking or zero-variance failure modes.

