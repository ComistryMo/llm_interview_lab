# INT-004 · Design Failure Fallbacks and Rollout

## Scenario

A fictional assistant summarizes customer conversations for internal teams. A pilot shows useful summaries, occasional unsupported claims, and variable latency.

## Primary question

Design the production path from request to displayed result, including validation, confidence handling, user controls, observability, staged rollout, incident response, and rollback.

## Constraints

- Model output is untrusted data.
- Some requests contain sensitive text.
- The service must degrade without blocking the underlying non-AI workflow.

## Follow-up axes

The interviewer may remove human review, tighten the SLO, or introduce a provider outage.
