# ATT-002 — Scaled Dot-Product Attention

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
def scaled_dot_product_attention(query, key, value, mask=None, causal=False) -> tuple[torch.Tensor, torch.Tensor]:
```

## Tensor/state contract

- `query`, `key`, `value` are floating `(batch, heads, q_len/k_len, head_dim)`; key/value share length, dtype, and device.
- Compute scores divided by `sqrt(head_dim)`, apply boolean allowed-position mask before stable Softmax, and optionally apply a square causal mask.
- Every query row must allow at least one key; return output `(B,H,Q,Dv)` and probabilities `(B,H,Q,K)`.
- Do not use framework SDPA/MHA; masked probabilities are exact zero and gradients remain connected.

## Acceptance

Run `llm-lab test ATT-002 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

