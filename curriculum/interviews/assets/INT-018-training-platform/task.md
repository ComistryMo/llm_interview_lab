# INT-018 · Design a Multi-Team Training Platform

## Scenario

Several fictional teams train models with different data, frameworks, GPU counts, and checkpoint sizes. They need reproducibility, fair scheduling, isolation, observability, and recovery without a single central team operating every job manually.

## Primary question

Design the control and data paths. Clarify workload assumptions, job contract, scheduling, artifact lineage, secrets, distributed launch, checkpointing, observability, failure recovery, and cost controls.

## Constraints

- Training code is user supplied and may fail, but this is not a hostile multi-tenant sandbox design exercise.
- Datasets and credentials have different access policies.
- Avoid assuming one distributed framework.

## Follow-up axes

The interviewer may add preemption, spot capacity, multi-region data, or a large queue of small jobs.
