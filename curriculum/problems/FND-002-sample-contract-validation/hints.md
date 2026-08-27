# Hints — FND-002

## H1 — concept

Re-read the strict runtime types, mutation rule, and exact return contract. Type annotations alone do not validate input.

## H2 — structure

Separate validation from the main transformation. Identify which containers must be copied before returning or yielding.

## H3 — steps

Validate outer arguments first, validate each nested value at the point it is consumed, then build the result in one forward pass. Test one valid case and one invalid boundary before running the full suite.

These hints intentionally omit a complete implementation.

