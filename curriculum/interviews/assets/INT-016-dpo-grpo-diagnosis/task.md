# INT-016 · Diagnose DPO versus GRPO Objectives

## Scenario

A fictional team observes stable DPO training but unstable grouped policy optimization: some groups have identical rewards, completion lengths vary widely, and KL grows after an update.

## Primary question

Explain the different data and objective flows, diagnose the observed failure modes, identify invariants and tiny cases to test, and propose a safe investigation order.

## Constraints

- Keep current, old, and reference policy quantities distinct.
- Address masks and sequence lengths explicitly.
- Do not hide zero reward variance behind an arbitrary epsilon conclusion.

## Follow-up axes

The interviewer may change clipping, advantage normalization, reward scale, or the placement of KL.
