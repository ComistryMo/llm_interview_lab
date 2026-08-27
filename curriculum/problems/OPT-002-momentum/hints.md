# Hints — OPT-002

## H1 — concept

Separate parameter gradients, optimizer state, and the parameter update. Decide exactly when a missing gradient changes state.

## H2 — structure

Validate every parameter/state pair before entering a no-grad update block. Build fresh detached state in parameter order.

## H3 — steps

For each valid gradient, update the documented state equations, compute any corrected quantities from the incremented step, and only then mutate the parameter. Use a one-element float64 hand calculation.

No complete implementation is included.

