# Hints — VLM-007

## H1 — concept

Separate the three masks from the causal shift.  The assistant mask says what
could be supervised; attention/padding and image positions can remove targets.
The labels are metadata, while logits remain the only differentiable input.

## H2 — structure

Validate the complete batch contract before allocating outputs.  Build a fresh
label tensor, derive a boolean valid mask, then inspect the target-aligned
slice after shifting.  Reduce cross-entropy over valid tokens rather than over
padding or visual placeholders.

## H3 — debugging questions

- Which input position predicts each shifted target?
- What should happen when an image placeholder is accidentally marked as an
  assistant span?
- Can ignored positions contain an ID outside the language vocabulary?
- How will you report a sample whose assistant span disappears after masking?

No complete implementation is included.
