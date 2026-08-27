# NNL-002 — Embedding Layer

## Goal

Implement a reusable neural-network layer from explicit Parameters and primitive tensor operations.

## Interface

```python
class ManualEmbedding(torch.nn.Module):
    def __init__(self, num_embeddings: int, embedding_dim: int, padding_idx: int | None = None): ...
    def forward(self, input_ids: torch.Tensor) -> torch.Tensor: ...
```

## Contract

- Register one weight parameter `(num_embeddings, embedding_dim)` initialized from a standard normal distribution.
- Accept arbitrary-shape `torch.long` IDs and append `embedding_dim` to the output shape.
- If `padding_idx` is set, padding outputs are exact zeros and its weight row receives zero gradient.
- Reject out-of-range IDs; do not use `torch.nn.Embedding` or `torch.nn.functional.embedding`.

## Acceptance

Run `llm-lab test NNL-002 --profile <id>`. Tests inspect registered parameters, shapes, initialization, values, dtype/device, gradients, invalid inputs, and reference alignment.

## Oral defense

Explain parameter shapes and initialization, derive the forward equation, identify gradient destinations, and state time/space complexity.

