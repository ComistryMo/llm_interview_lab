# FND-006 — Mini-Batch Iterator

## Goal

Create deterministic, lazy mini-batches without changing or aliasing the input list.

## Interface

```python
def iter_minibatches(items: list[object], batch_size: int, drop_last: bool = False) -> Iterator[list[object]]:
```

## Contract

- `items` is an exact list, `batch_size` a strict positive integer, and `drop_last` an exact bool.
- Yield new lists in original order; the last short batch is kept unless `drop_last=True`.
- Empty input yields no batches; invalid arguments raise `ValueError`.
- Return an iterator and do not mutate or expose slices that alias the input container.

## Acceptance

Run `llm-lab test FND-006 --profile <id>`. Public tests check normal, boundary, error, determinism, and non-mutation behavior. Do not use company data or copy an external exercise.

## Oral defense

Explain the runtime contract, one rejected edge case, time and auxiliary-space complexity, and why the implementation does not mutate its input.

