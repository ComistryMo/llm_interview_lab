# Hints — NNL-001

## H1 — concept

List trainable Parameters separately from ordinary attributes. Write the exact final-dimension equation and initialization range.

## H2 — structure

Validate constructor arguments before registering state. In forward, validate rank/last dimension, compute with primitive tensor operations, and preserve dtype/device.

## H3 — steps

Create parameters with documented shapes, initialize them under no-grad semantics, implement the reference equation, then test a one-row hand-computed input before checking gradients.

No complete implementation is included.

