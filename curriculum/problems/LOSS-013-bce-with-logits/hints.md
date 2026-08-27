# Hints — LOSS-013

## H1 — concept

Start from the mathematical definition and identify where direct exponentiation or logarithms can overflow or underflow.

## H2 — structure

Validate shape/dtype/device and reduction first. Compute unreduced per-example values with a max-shift identity, then apply reduction once.

## H3 — steps

Derive a stable scalar expression, lift it to the documented tensor axis, isolate ignored elements if any, and compare a tiny float64 example to the official reference.

No complete implementation is included.

