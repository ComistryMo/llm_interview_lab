# INT-024 · Audit Benchmark Leakage and Safety Coverage

## Scenario

A fictional model release shows strong aggregate benchmark gains. Some evaluation prompts were used during prompt tuning, an LLM judge shares a model family with the candidate, and rare safety cases are pooled into one average.

## Primary question

Audit whether the release claim is trustworthy. Cover provenance, contamination, sampling, rubric, judge validation, rare-risk reporting, uncertainty, release gates, and remediation.

## Constraints

- Do not discard inconvenient results without a predeclared reason.
- Do not treat model-family diversity as proof of judge independence.
- Preserve a protected set for future decisions.

## Follow-up axes

The interviewer may reveal duplicate paraphrases, annotator disagreement, distribution shift, or too few severe cases for a stable rate.
