# ATT-005 — Multi-Query Attention

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
def multi_query_attention(query, key, value, num_heads, mask=None, causal=False) -> torch.Tensor:
```

## Tensor/state contract

- `query` is `(B,Q,num_heads*head_dim)` while shared `key` is `(B,K,head_dim)` and `value` `(B,K,value_dim)`.
- Broadcast the single KV head across query heads without materializing independent learned KV projections.
- Apply scaled attention per query head and return concatenated `(B,Q,num_heads*value_dim)`.
- Support masks/causal mode and preserve gradients; do not use framework SDPA/MHA or repeat-interleave KV copies.

## Acceptance

Run `llm-lab test ATT-005 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

