# AGT-002 — Tool Registry

## Goal

Implement one deterministic, local-only Agent data or runtime primitive.

## Interface

```python
class ToolRegistry:
    def register(self, schema, handler) -> None: ...
    def call(self, name, arguments) -> object: ...
```

## Contract

- Register a validated schema with one callable handler; reject duplicate names and non-callables.
- Expose sorted `names` without mutable registry internals.
- `call` validates required/unknown arguments and supported primitive types before invoking the handler.
- Unknown tools or invalid arguments raise `ValueError`; handler exceptions propagate without retry.

## Safety boundary

These exercises execute only user-trusted local functions. They do not provide network, process, permission, or multi-tenant isolation.

## Acceptance

Run `llm-lab test AGT-002 --profile <id>`. Tests cover valid flows, malformed actions/data, deterministic ordering, state isolation, termination, and non-mutation.

## Oral defense

Explain schema validation, state transitions, invalid-action behavior, termination, replay determinism, and what production isolation remains out of scope.

