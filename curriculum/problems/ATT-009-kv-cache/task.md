# ATT-009 — KV Cache

## Goal

Implement the attention or inference-state contract from primitive PyTorch operations.

## Interface

```python
class KVCache:
    def __init__(self, batch_size, max_length, num_kv_heads, head_dim, *, dtype, device): ...
    def append(self, key, value) -> tuple[torch.Tensor, torch.Tensor]: ...
```

## Tensor/state contract

- Preallocate key/value storage `(batch_size, num_kv_heads, max_length, head_dim)` and expose read-only integer `length`.
- `append` accepts matching `(B,H,new_tokens,D)` tensors, copies them into the next positions under no-grad semantics, and increments length atomically.
- Return views limited to populated positions; reject overflow, shape/dtype/device mismatch before mutation.
- Inference cache tensors are detached and the cache does not promise a malicious-code sandbox or training gradients.

## Acceptance

Run `llm-lab test ATT-009 --profile <id>`. Tests cover shapes, numerical/reference alignment, mask behavior, dtype/device, gradients or inference detachment, invalid inputs, and non-mutation.

## Oral defense

Draw every shape transition, explain scaling and mask placement, compare MHA/MQA/GQA KV heads where relevant, and state prefill/decode time and memory costs.

