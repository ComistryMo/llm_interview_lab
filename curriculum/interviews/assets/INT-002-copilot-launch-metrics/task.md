# INT-002 · Define Launch Metrics for an AI Copilot

## Scenario

A fictional document editor is piloting an AI drafting copilot. Users can accept, edit, reject, or ignore suggestions. The product team wants one launch dashboard but has not agreed on what “better” means.

## Primary question

Design an evaluation and launch metric system. Cover the outcome hierarchy, offline set, online experiment, segmentation, guardrails, logging needed for diagnosis, and a launch/rollback decision.

## Constraints

- Acceptance rate alone is not a sufficient quality measure.
- Do not assume logged text can be retained indefinitely.
- State how novelty effects and selection bias could mislead the decision.

## Follow-up axes

The interviewer may introduce high latency, low-frequency harmful suggestions, or disagreement between offline and online signals.
