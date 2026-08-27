# AGT-009 — Trajectory JSONL

## Goal

Implement one deterministic, local-only Agent data or runtime primitive.

## Interface

```python
class TrajectoryJsonl:
    @staticmethod
    def write(path, events) -> int: ...
    @staticmethod
    def read(path) -> Iterator[dict[str, object]]: ...
```

## Contract

- Each event is an exact dictionary with strict integer `step`, non-empty string `type`, and dictionary `payload`.
- Steps are contiguous from zero in physical file order; reject duplicates, gaps, blank lines, non-object JSON, or invalid UTF-8.
- Write compact UTF-8 JSONL and return event count; read lazily as an iterator.
- Return defensive objects and never reorder using timestamps; normal filesystem errors propagate.

## Safety boundary

These exercises execute only user-trusted local functions. They do not provide network, process, permission, or multi-tenant isolation.

## Acceptance

Run `llm-lab test AGT-009 --profile <id>`. Tests cover valid flows, malformed actions/data, deterministic ordering, state isolation, termination, and non-mutation.

## Oral defense

Explain schema validation, state transitions, invalid-action behavior, termination, replay determinism, and what production isolation remains out of scope.

