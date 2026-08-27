# INT-011 · Design a Bounded Tool-Calling Loop

## Scenario

A fictional assistant can search a read-only knowledge source and draft a ticket. Users must approve any ticket creation. Tool responses and model output may be malformed.

## Primary question

Design the agent state machine, tool contract, parser and validation boundaries, retry and timeout behavior, user approval, stop conditions, trajectory record, and evaluation strategy.

## Constraints

- A model-proposed action is not authorization.
- The loop must terminate deterministically.
- Tool output is untrusted data.

## Follow-up axes

The interviewer may add repeated actions, a slow tool, conflicting observations, or a model that ignores an error.
