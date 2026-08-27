# INT-007 · Design a Reliable RAG Answer Path

## Scenario

A fictional internal knowledge assistant answers questions from documents with different owners, access levels, update schedules, and authority.

## Primary question

Design the request path from identity and query to retrieval, generation, citation, validation, feedback, and fallback. Explain freshness, authorization, observability, evaluation, and cost/latency trade-offs.

## Constraints

- Retrieval must not cross user permissions.
- Conflicting sources are possible.
- “No reliable answer” is a valid outcome.

## Follow-up axes

The interviewer may introduce stale indexes, weak recall, prompt injection in documents, or a strict latency SLO.
