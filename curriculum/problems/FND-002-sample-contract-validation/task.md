# FND-002 — Sample Contract Validation

## Goal

Validate one toy inference sample and return a defensive normalized copy.

## Interface

```python
def validate_sample(sample: dict[str, object]) -> dict[str, object]:
```

## Contract

- `sample` must have exact type `dict` and contain `sample_id`, `label`, and `predictions`.
- `sample_id` is a non-empty `str`; `label` and every prediction are strict integers (`bool` is rejected).
- `predictions` is a non-empty exact `list`; contract violations raise `ValueError`.
- Return a new dictionary with a newly copied predictions list; never mutate or alias the input list.

## Acceptance

Run `llm-lab test FND-002 --profile <id>`. Public tests check normal, boundary, error, determinism, and non-mutation behavior. Do not use company data or copy an external exercise.

## Oral defense

Explain the runtime contract, one rejected edge case, time and auxiliary-space complexity, and why the implementation does not mutate its input.

