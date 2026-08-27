# FND-004 — Hard Sample Summary

## Goal

Aggregate deterministic error statistics from validated repeated-inference samples.

## Interface

```python
def summarize_hard_samples(samples: list[dict[str, object]]) -> dict[str, int | float]:
```

## Contract

- Validate the outer list and every sample with the same strict contract as FND-002.
- Return exactly: `total_samples`, `total_predictions`, `total_errors`, `hard_samples`, `error_rate`.
- A hard sample has at least one wrong prediction; empty input returns integer zeros and `error_rate` 0.0.
- Compute rate as total errors divided by total predictions and do not mutate inputs.

## Acceptance

Run `llm-lab test FND-004 --profile <id>`. Public tests check normal, boundary, error, determinism, and non-mutation behavior. Do not use company data or copy an external exercise.

## Oral defense

Explain the runtime contract, one rejected edge case, time and auxiliary-space complexity, and why the implementation does not mutate its input.

