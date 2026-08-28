# INT-022 · Size an LLM Serving Fleet

## Scenario

A fictional service hosts one decoder model for interactive and batch requests. Traffic has bursts, prompt and output lengths vary, and the product has separate first-token and end-to-end latency objectives.

## Primary question

Build a capacity model and serving design. Cover workload measurements, memory, prefill/decode, batching, admission, queues, replicas, failure handling, observability, and load-test validation.

## Constraints

- Do not use average sequence length as the only workload description.
- Distinguish time-to-first-token from token generation latency.
- State assumptions instead of inventing model or hardware numbers.

## Follow-up axes

The interviewer may add multi-tenancy, a context-length spike, quantization, or a provider-style rate limit.
