# Hints for FND-001

Use only the lowest level you need. Record the highest help level in your
learning history.

## H1 — concepts to inspect

- A type annotation documents intent but does not validate runtime values.
- Check the distinction between an iterable element and its index.
- Review the exact relationship among `bool`, `int`, `isinstance`, and `type`.

## H2 — requirement decomposition

Separate the contract into container validation, empty-input validation,
element validation, and counting. Decide which checks must happen before any
result can be returned.

## H3 — implementation structure

Use one validation phase followed by one counting phase. Each validation
failure should use the required exception type. The counting phase should read
elements without assigning into the input list.

These hints intentionally omit complete code and exact statements.
