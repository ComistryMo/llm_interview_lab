# INT-020 · Schedule Heterogeneous Training Jobs

## Scenario

A fictional GPU cluster runs urgent debugging jobs, long distributed runs, and many small experiments. Large jobs suffer starvation, while strict FIFO leaves GPUs idle because requested shapes do not fit.

## Primary question

Design scheduling policy and mechanisms for admission, queueing, placement, fairness, utilization, preemption, quotas, backfill, and observability. State which objectives conflict.

## Constraints

- GPUs have different memory and interconnect topology.
- Some jobs are restartable; others have expensive checkpoints.
- Do not claim one scalar priority solves fairness.

## Follow-up axes

The interviewer may add deadline jobs, spot nodes, gang scheduling, or inaccurate runtime estimates.
