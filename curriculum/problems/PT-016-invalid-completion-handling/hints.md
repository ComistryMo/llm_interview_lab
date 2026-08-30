# Hints — PT-016

## H1 — concept

Treat verifier validity as a separate boolean axis.  First decide which
rewards participate in each group statistic; only then form normalized
advantages.  Invalid slots must not be represented by a numeric sentinel that
can enter a reduction.

## H2 — structure

Use a safe masked view for accumulation, count valid completions per row, and
use population variance.  Handle zero/near-zero variance and empty rows
explicitly.  Return a detached advantage tensor and a defensive mask copy.

## H3 — debugging questions

- Does a huge invalid reward change the mean of its group?
- What should a one-sample group contribute to a policy loss?
- Can a NaN be present in an invalid slot without poisoning the result?
- Why is an advantage tensor derived from a verifier not a policy-gradient
  input?

No complete implementation is included.
