# Hints — ATT-009

## H1 — concept

Write query-head and KV-head shapes separately. A mask describes allowed key positions and must affect scores before Softmax.

## H2 — structure

Validate batch/head/length dimensions first. Reshape into explicit heads, compute stable attention, then transpose and concatenate only once.

## H3 — steps

Build a tiny one-batch example, derive its score shape, apply scaling and mask, multiply probabilities by values, and verify the final layout. For cache state, validate the entire append before copying.

No complete implementation is included.

