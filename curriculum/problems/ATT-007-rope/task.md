# ATT-007 — Rotary Position Embedding

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
```

## Tensor/state contract

- `x` is floating `(batch, heads, sequence, head_dim)` with even `head_dim`; `cos` and `sin` are `(sequence, head_dim/2)`.
- Rotate adjacent even/odd feature pairs using the supplied cosine and sine values.
- Return the same shape/dtype/device, preserve pairwise norms and gradients, and do not mutate inputs.
- Reject mismatched shapes/dtypes/devices; do not use a library RoPE helper.

## Acceptance

Run `llm-lab test ATT-007 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

