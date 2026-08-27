# Hints — TNS-002

## H1 — concept

Write every intermediate shape on paper. Check dtype, device, contiguity, and whether the operation remains connected to autograd.

## H2 — structure

Validate rank and compatible dimensions first. Build the result with tensor operations, then assert the documented final shape mentally.

## H3 — steps

Create the minimal index/view/broadcast tensor on the input device, apply the target operation on the documented axis, and avoid in-place writes. Compare one tiny hand-computed tensor before the full suite.

No complete implementation is included.

