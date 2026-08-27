# PT-001 — SFT Label Mask

## Goal

Implement one auditable post-training data or objective primitive.

## Interface

```python
def build_sft_labels(input_ids, response_mask, pad_token_id, ignore_index=-100) -> torch.Tensor:
```

## Contract

- `input_ids` is long `(batch, sequence)` and `response_mask` is boolean with the same shape/device.
- Return a cloned long label tensor: response, non-padding positions keep token IDs; all other positions equal strict-int `ignore_index`.
- Reject rows with no supervised response token and reject `pad_token_id == ignore_index`.
- Do not mutate or alias inputs; output remains on the input device.

## Acceptance

Run `llm-lab test PT-001 --profile <id>`. Tests cover shapes, masks, stable values, gradients, degenerate groups, invalid data, and input immutability.

## Oral defense

Trace data from tokens or rewards to the returned objective, derive the formula, explain masking/reduction, and identify reward-hacking or zero-variance failure modes.

