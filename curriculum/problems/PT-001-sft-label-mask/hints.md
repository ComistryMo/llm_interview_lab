# Hints — PT-001

## H1 — concept

Separate data validity, token/group axes, and the scalar objective. Write which tensors should and should not carry gradients.

## H2 — structure

Validate all aligned shapes first. Compute unreduced token or example values, apply masks, then reduce over the documented denominator.

## H3 — steps

Use one tiny batch with hand-computed tokens or rewards, derive the stable per-item expression, handle the degenerate case explicitly, and compare values plus gradients.

No complete implementation is included.

