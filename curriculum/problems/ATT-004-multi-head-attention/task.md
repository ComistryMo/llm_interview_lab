# ATT-004 — Multi-Head Attention

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
def multi_head_attention(query, key, value, num_heads, mask=None, causal=False) -> torch.Tensor:
```

## Tensor/state contract

- Inputs are pre-projected rank-3 `(batch, length, hidden)` tensors with equal query/key hidden size divisible by strict positive `num_heads`.
- Split hidden dimensions into heads, apply scaled attention independently per head, concatenate in original hidden order.
- Value hidden size is also divisible by `num_heads`; output is `(batch, q_len, value_hidden)`.
- Support broadcastable boolean masks and causal mode; do not use framework MHA/SDPA.

## Acceptance

Run `llm-lab test ATT-004 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

