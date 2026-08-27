# INT-005 · Design an Online Experiment with Guardrails

## Scenario

A fictional search product wants to replace a deterministic query suggestion with model-generated suggestions for a subset of traffic.

## Primary question

Design the experiment from hypothesis to decision. Include unit of randomization, eligibility, baseline, primary metric, guardrails, sample and duration reasoning, novelty and interference risks, monitoring, and rollback.

## Constraints

- Some users share accounts.
- Suggestion generation has a long-tail latency distribution.
- Harmful text is rare but material.

## Follow-up axes

The interviewer may present a positive primary metric with worse guardrails or inconsistent segment results.
