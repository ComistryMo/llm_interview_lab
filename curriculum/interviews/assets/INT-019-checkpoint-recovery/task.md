# INT-019 · Recover a Corrupted Training Resume

## Scenario

A fictional distributed training job resumes without crashing, but loss jumps, optimizer steps appear inconsistent, and one rank reports a different shard checksum.

## Primary question

Describe incident containment, evidence collection, consistency checks, root-cause isolation, a safe recovery decision, and improvements to checkpoint creation and restore.

## Constraints

- A load call succeeding does not prove semantic consistency.
- Do not overwrite the last known-good checkpoint during investigation.
- Consider model, optimizer, scheduler, RNG, sampler, and topology state.

## Follow-up axes

The interviewer may reveal partial uploads, changed world size, a non-atomic manifest, or version skew.
