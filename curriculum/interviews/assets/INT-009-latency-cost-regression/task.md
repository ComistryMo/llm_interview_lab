# INT-009 · Diagnose a Latency and Cost Regression

## Scenario

After a fictional AI assistant release, p95 latency rises by 70% and cost per successful task rises by 40%, while request volume is nearly unchanged. Recent changes include longer prompts, a new retry policy, and a model routing rule.

## Primary question

Describe the investigation order, evidence needed to attribute the regression, immediate mitigation, durable fixes, and how you would prevent recurrence.

## Constraints

- Correlated deployments are not automatically causal.
- Do not expose prompt contents or API keys in logs.
- Quality must be measured during mitigation.

## Follow-up axes

The interviewer may reveal cache misses, provider throttling, output-token growth, or one affected tenant segment.
