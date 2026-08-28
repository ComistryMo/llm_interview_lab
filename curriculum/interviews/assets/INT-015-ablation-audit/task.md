# INT-015 · Audit an Ablation Claim

## Scenario

A fictional project report claims a training technique improves a benchmark by 2.1 points. The new run also uses more data, a different seed, a revised evaluator, and a larger token budget.

## Primary question

Audit the claim. Identify confounders, reconstruct the minimum fair comparison, define reruns and uncertainty, explain which conclusions are currently supported, and propose a decision-safe report.

## Constraints

- Do not assume benchmark points are statistically independent.
- Treat evaluator changes as a possible intervention.
- Do not invent missing runs or standard deviations.

## Follow-up axes

The interviewer may limit compute, reveal only one checkpoint, or show mixed results across slices.
