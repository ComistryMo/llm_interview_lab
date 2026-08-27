# PT-002 — Token / Sequence Logprob

## Goal

Implement one auditable post-training data or objective primitive.

## Interface

```python
def token_sequence_logprobs(logits, token_ids, mask) -> tuple[torch.Tensor, torch.Tensor]:
```

## Contract

- `logits` is floating `(B,S,V)`, `token_ids` is long `(B,S)`, and boolean `mask` has the same token shape/device.
- Compute selected token log-probabilities with stable LogSumExp; do not call framework log-softmax/cross-entropy.
- Return masked token logprobs `(B,S)` with exact zeros outside mask and sequence sums `(B,)`.
- Validate IDs and require at least one selected token per row; preserve logits gradients and inputs.

## Acceptance

Run `llm-lab test PT-002 --profile <id>`. Tests cover shapes, masks, stable values, gradients, degenerate groups, invalid data, and input immutability.

## Oral defense

Trace data from tokens or rewards to the returned objective, derive the formula, explain masking/reduction, and identify reward-hacking or zero-variance failure modes.

