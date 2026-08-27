# PT-015 — GRPO Clipped Loss

## Goal

Implement one auditable post-training data or objective primitive.

## Interface

```python
def grpo_clipped_loss(logprobs, old_logprobs, advantages, mask, clip_eps) -> torch.Tensor:
```

## Contract

- `logprobs`/`old_logprobs` are finite floating `(B,G,S)` tensors; `advantages` is detached `(B,G)` and `mask` boolean `(B,G,S)`.
- Compute ratio `exp(logprobs-old_logprobs)`, broadcast advantages over tokens, and use the minimum of unclipped/clipped surrogates.
- Return the negative mean over valid mask positions only; require at least one valid token and `0 < clip_eps < 1`.
- Preserve gradients only through current logprobs; do not mutate inputs.

## Acceptance

Run `llm-lab test PT-015 --profile <id>`. Tests cover shapes, masks, stable values, gradients, degenerate groups, invalid data, and input immutability.

## Oral defense

Trace data from tokens or rewards to the returned objective, derive the formula, explain masking/reduction, and identify reward-hacking or zero-variance failure modes.

