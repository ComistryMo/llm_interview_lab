# ATT-006 — Grouped-Query Attention

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
def grouped_query_attention(query, key, value, num_query_heads, num_kv_heads, mask=None, causal=False) -> torch.Tensor:
```

## Tensor/state contract

- Query hidden is `num_query_heads*head_dim`; key hidden is `num_kv_heads*head_dim`; value hidden is `num_kv_heads*value_dim`.
- Require `num_query_heads % num_kv_heads == 0`; consecutive groups of query heads share one KV head.
- Return `(B,Q,num_query_heads*value_dim)` after scaled attention, with mask/causal semantics.
- Preserve gradient sharing and avoid framework SDPA/MHA.

## Acceptance

Run `llm-lab test ATT-006 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

