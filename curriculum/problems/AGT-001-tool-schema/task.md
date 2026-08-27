# AGT-001 — Tool Schema

## Goal

Implement one deterministic, local-only Agent data or runtime primitive.

## Interface

```python
def validate_tool_schema(schema: dict[str, object]) -> dict[str, object]:
```

## Contract

- Require an exact dictionary with non-empty `name`, non-empty `description`, and `parameters`.
- Name matches lowercase letters/digits/underscore and starts with a letter; parameters is a JSON-Schema-like object with `type: object`, `properties`, and `required`.
- Each property has one supported primitive type; required names must exist in properties; unknown top-level fields are rejected.
- Return a deep-enough defensive copy for all nested containers; invalid input raises `ValueError`.

## Safety boundary

These exercises execute only user-trusted local functions. They do not provide network, process, permission, or multi-tenant isolation.

## Acceptance

Run `llm-lab test AGT-001 --profile <id>`. Tests cover valid flows, malformed actions/data, deterministic ordering, state isolation, termination, and non-mutation.

## Oral defense

Explain schema validation, state transitions, invalid-action behavior, termination, replay determinism, and what production isolation remains out of scope.

