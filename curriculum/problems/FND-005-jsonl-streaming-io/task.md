# FND-005 — JSONL Streaming I/O

## Goal

Read and write UTF-8 JSON Lines without loading an entire dataset into memory.

## Interface

```python
class JsonlIO:  # static read(path) and write(path, records)
```

## Contract

- `JsonlIO.read(path)` returns an iterator of JSON objects and reports malformed or blank lines as `ValueError` with a 1-based line number.
- `JsonlIO.write(path, records)` writes one compact UTF-8 JSON object per line and returns the number written.
- Reject non-object records with `ValueError`; propagate normal filesystem errors.
- Reading must be lazy and both methods must work with `str` or `pathlib.Path` paths.

## Acceptance

Run `llm-lab test FND-005 --profile <id>`. Public tests check normal, boundary, error, determinism, and non-mutation behavior. Do not use company data or copy an external exercise.

## Oral defense

Explain the runtime contract, one rejected edge case, time and auxiliary-space complexity, and why the implementation does not mutate its input.

