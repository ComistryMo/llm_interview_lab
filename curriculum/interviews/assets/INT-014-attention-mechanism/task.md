# INT-014 · Explain an Attention Experiment Mechanistically

## Scenario

A fictional experiment replaces multi-head attention with grouped-query attention. Decode throughput improves, validation loss changes slightly, and one long-context slice regresses.

## Primary question

Explain the mechanism that could produce these results, the tensor and cache differences, alternative causes, experiments needed to isolate them, and the decision you would make with current evidence.

## Constraints

- Do not infer causality from one aggregate run.
- Distinguish prefill, decode, memory, optimization, and task-quality effects.
- State assumptions about head counts and checkpoint conversion.

## Follow-up axes

The interviewer may change batch size, context length, hardware, or the number of key/value heads.
