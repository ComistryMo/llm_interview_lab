# INT-012 · Debug a Repeating Agent Trajectory

## Scenario

A fictional agent repeatedly calls the same search tool with equivalent arguments, receives nearly identical observations, and reaches the maximum step count. The final answer is empty.

## Primary question

Explain how you would reproduce and localize the loop, what trajectory evidence is required, plausible root causes, immediate safeguards, durable fixes, and regression tests.

## Constraints

- Do not assume the model alone is at fault.
- Preserve enough evidence to distinguish parser, state, tool, prompt, and policy faults.
- Avoid storing unrestricted sensitive tool output.

## Follow-up axes

The interviewer may reveal nondeterministic tool order, stale memory, a swallowed exception, or semantically equivalent but textually different arguments.
