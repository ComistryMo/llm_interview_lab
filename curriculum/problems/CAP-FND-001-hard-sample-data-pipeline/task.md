# CAP-FND-001 — Hard Sample Data Pipeline

## Goal

Combine the six Python Data Reliability skills into one deterministic local
JSONL pipeline. Read and validate every sample, count prediction errors, keep
hard samples, aggregate their labels, persist them, and form mini-batches.

## Interface

```python
def run_hard_sample_pipeline(
    input_path: str | Path,
    output_path: str | Path,
    min_errors: int,
    batch_size: int,
) -> dict[str, object]:
```

## Contract

- Each non-blank UTF-8 JSONL line must be an object with exactly
  `sample_id`, `label`, and `predictions`, using the strict FND-002 types.
- `min_errors` and `batch_size` are strict positive integers; reject `bool`.
- A hard sample has at least `min_errors` predictions different from `label`.
- Validate the whole input before replacing `output_path`; contract failures
  raise `ValueError` with a 1-based line number and leave an existing output
  unchanged. Normal filesystem errors propagate.
- Write compact JSONL defensive copies of hard samples in input order.
- Return exactly `input_samples`, `total_predictions`, `total_errors`,
  `hard_samples`, `label_counts`, and `batches`. `label_counts` counts hard
  samples by integer label; `batches` contains new lists, keeps the last short
  batch, and exactly matches output order.
- Do not mutate the input file or alias mutable nested lists between returned
  batches and internal records.

## Acceptance

Run `llm-lab test CAP-FND-001 --profile <id>`. The Capstone unlocks only after
FND-001 through FND-006 are all mastered.
