# INT-013 · Evaluate a Long-Horizon Agent

## Scenario

A fictional research assistant completes multi-step tasks using search, file notes, and a calculator in a resettable environment. Successful outcomes may still contain wasteful or unsafe trajectories.

## Primary question

Design an evaluation that measures final outcome, trajectory quality, recovery, cost, and safety. Explain task sampling, environment versioning, judge calibration, leakage controls, replay, and diagnosis.

## Constraints

- Final success alone is insufficient.
- Environment state must be reproducible.
- AI judge scores require validation against human evidence.

## Follow-up axes

The interviewer may introduce stochastic tools, long trajectories, sparse failures, or disagreement between final-state and trajectory evaluators.
