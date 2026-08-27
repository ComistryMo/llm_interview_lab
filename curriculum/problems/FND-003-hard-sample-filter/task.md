# FND-003 — Hard Sample Filter

## Goal

Select samples whose repeated predictions contain at least a threshold number of errors.

## Interface

```python
def mine_hard_samples(samples: list[dict[str, object]], min_errors: int = 1) -> list[dict[str, object]]:
```

## Contract

- `samples` must be an exact list; each item follows FND-002's strict sample contract.
- `min_errors` is a strict positive integer; invalid input raises `ValueError`.
- Return qualifying samples in original order as defensive copies with copied predictions lists.
- Do not mutate the outer list or any nested input list.

## Acceptance

Run `llm-lab test FND-003 --profile <id>`. Public tests check normal, boundary, error, determinism, and non-mutation behavior. Do not use company data or copy an external exercise.

## Oral defense

Explain the runtime contract, one rejected edge case, time and auxiliary-space complexity, and why the implementation does not mutate its input.

