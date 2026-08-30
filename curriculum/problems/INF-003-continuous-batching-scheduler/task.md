# INF-003 — Continuous Batching Scheduler

## Goal

Implement a deterministic, local scheduler for autoregressive serving.  It
must admit prompt-prefill work under a per-step token budget, interleave one
decode token per active request fairly, and release KV-cache capacity when a
request finishes, is cancelled, or expires.  The exercise models the control
plane only; it never calls a model or allocates GPU memory.

## Interface

```python
class ContinuousBatchScheduler:
    def __init__(
        self,
        max_active_tokens: int,
        max_prefill_tokens: int,
        max_decode_tokens: int = 1,
    ) -> None: ...

    def submit(
        self,
        request_id: str,
        prompt_tokens: int,
        max_new_tokens: int,
        deadline_step: int | None = None,
    ) -> None: ...

    def step(
        self,
        *,
        prefill_budget: int | None = None,
        decode_budget: int | None = None,
    ) -> dict[str, object]: ...

    def cancel(self, request_id: str) -> bool: ...
    def finish(self, request_id: str) -> bool: ...
    def snapshot(self) -> tuple[dict[str, object], ...]: ...

    @property
    def pending_ids(self) -> tuple[str, ...]: ...

    @property
    def active_ids(self) -> tuple[str, ...]: ...

    @property
    def completed_ids(self) -> tuple[str, ...]: ...

    @property
    def active_tokens(self) -> int: ...
```

## Contract

- Configuration values are positive Python integers (booleans are not
  accepted).  `max_active_tokens` is resident KV capacity; prefill consumes
  `prompt_tokens`, and each scheduled decode consumes one additional resident
  token.  A request must have `0 < prompt_tokens < max_active_tokens` and
  `max_new_tokens > 0`.
- `submit` appends a request to a FIFO queue.  IDs are non-empty strings and
  globally unique for the lifetime of the scheduler, including terminal
  requests.  `deadline_step`, when present, is a non-negative absolute step
  number and must not be in the past.  The scheduler starts at step `0`.
- `step` advances the step number by one.  At its beginning, queued or active
  requests whose deadline is strictly before the new step expire and release
  any resident tokens.  Expiration is reported separately from user
  cancellation.  Optional budgets are non-negative integers no greater than
  their configured maxima; `0` performs no work for that phase.
- Admission is FIFO and stops at the first queued request that does not fit
  both the remaining prefill budget and resident-token capacity (no
  head-skipping).  Newly admitted requests are *not* decoded in the same
  call.  This makes prefill/decode boundaries explicit and reproducible.
- Decode uses a persistent round-robin order over active requests.  Each
  active request receives at most one token per `step` call; at most
  `decode_budget` requests and available resident-token slots are served.
  Increment `generated_tokens`; a request automatically completes when it
  reaches `max_new_tokens`, and its resident tokens are released immediately.
- `cancel` removes a queued or active request, releases active capacity, and
  returns `True`; `finish` completes an active request and releases capacity.
  Both return `False` for unknown or already-terminal IDs.  Terminal IDs
  cannot be resubmitted.
- `step` returns a fresh dictionary with tuple-valued `admitted`, `decoded`,
  `completed`, and `expired` IDs, plus integer `prefill_tokens`,
  `decode_tokens`, `active_tokens`, `step`, and tuple snapshots `queued` and
  `active`.  `snapshot()` returns fresh record dictionaries in request
  submission order; mutating a returned record must not mutate scheduler state.
- No networking, threads, wall-clock sleeps, model calls, or GPU framework is
  required.  Preserve deterministic ordering and never expose mutable
  internal queues.

## Acceptance

Run `llm-lab test INF-003 --profile <id>`.  Public tests cover FIFO admission,
prefill and KV budgets, round-robin fairness, automatic completion, manual
finish/cancel, deadline expiration, zero-budget boundaries, state snapshots,
input validation, and terminal-capacity release.

## Oral defense

- Draw the request state machine and distinguish queued, active, completed,
  cancelled, and expired states.
- Explain why admission is limited by prompt tokens while decode consumes one
  KV token per active request, and why reserving the entire maximum output can
  waste capacity.
- Demonstrate how a persistent round-robin cursor prevents a long request
  from starving later requests when decode budget is smaller than batch size.
- Explain head-of-line blocking versus skipping a large request, and state
  which policy a production serving system might choose for latency goals.
- State what a real scheduler would add for cancellation races, tenant
  fairness, GPU kernel packing, prefix-cache ownership, and wall-clock
  deadlines.
