# INT-023 · Debug KV Cache Throughput Collapse

## Scenario

A fictional serving release changes cache block allocation. Memory utilization looks lower, yet decode throughput drops and p99 latency rises under long-context traffic. Short prompts remain healthy.

## Primary question

Describe how you would isolate cache layout, fragmentation, scheduler, copy, kernel, and workload causes. Define the necessary traces, controlled experiments, immediate mitigation, and regression protection.

## Constraints

- Lower allocated memory does not prove less memory traffic.
- Separate logical cache occupancy from physical allocation and movement.
- Preserve output correctness while changing the cache path.

## Follow-up axes

The interviewer may reveal eviction churn, block-table misses, non-contiguous copies, or one affected batch-size range.
