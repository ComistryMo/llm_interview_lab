# PT-016 — Invalid Completion Handling

## Goal

Implement the small but consequential data contract between a verifier and a
GRPO-style trainer.  A prompt can have several sampled completions; some may
be malformed, truncated, or rejected by a verifier.  Invalid rewards must not
enter the group mean/variance, and their policy advantages must be zero.

## Interface

```python
def normalize_valid_group_rewards(
    rewards: torch.Tensor,
    valid_mask: torch.Tensor,
    eps: float = 1e-6,
) -> tuple[torch.Tensor, torch.Tensor]:
    ...
```

## Contract

- `rewards` is a floating `(B, G)` tensor and `valid_mask` is boolean `(B, G)`
  on the same device.  `B > 0`, `G > 0`, and `eps` is finite and strictly
  positive.  Inputs are never mutated.
- For each prompt row, compute the population mean and standard deviation
  using **only** valid completions.  The statistic uses the valid count as the
  denominator (`unbiased=False`).  Invalid values are ignored entirely; an
  invalid slot may contain a sentinel NaN or infinity.
- Return `(advantages, kept_mask)`.  `advantages` has the same shape, dtype,
  and device as `rewards`; invalid slots are exactly zero.  `kept_mask` is a
  fresh boolean copy of `valid_mask` and is the mask a downstream policy loss
  should use.
- A row with at least two valid completions and standard deviation greater
  than `eps` receives `(reward - mean) / std` on its valid slots.  A row with
  zero/near-zero variance or only one valid completion receives zero
  advantages (but keeps its valid mask).  A row with no valid completion is
  retained as all-false/all-zero so callers can count or drop it; if the whole
  batch has no valid completion, raise `ValueError`.
- Rewards at valid positions must be finite.  The result is detached from any
  reward autograd graph: verifier rewards are training metadata, not a path
  for policy gradients.  Computation must remain finite for half/bfloat16
  inputs by using a suitable accumulation dtype before casting back.

## Acceptance

Run `llm-lab test PT-016 --profile <id>`.  Public tests cover filtered
statistics, invalid outliers and sentinel values, singleton/zero-variance
groups, all-invalid handling, dtype/device preservation, detached gradients,
shape/value validation, and input immutability.

## Oral defense

- Explain why including an invalid completion changes both the baseline and
  the scale of every valid advantage.
- Derive the population-variance formula and compare it with an unbiased
  sample standard deviation for tiny groups.
- Explain what to do with a group whose verifier rejects every completion and
  why silently treating it as reward zero is dangerous.
- State why rewards and advantages should be detached from the policy graph.
- Describe how NaN verifier sentinels can be accepted only in masked slots
  without allowing them to poison a reduction.
