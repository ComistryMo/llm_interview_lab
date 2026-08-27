# INT-008 · Debug Structured Output Failures

## Scenario

A fictional extraction service asks a model for JSON matching a schema. Production sees malformed JSON, valid JSON with invalid fields, and semantically unsupported values. Retries sometimes increase cost without improving success.

## Primary question

Propose a debugging sequence and a reliable response pipeline. Distinguish transport, syntax, schema, semantic, and source-grounding failures; define evidence, retry policy, fallback, and monitoring.

## Constraints

- Do not solve the problem by parsing with `eval`.
- Model output is untrusted.
- A valid schema does not prove a fact is supported.

## Follow-up axes

The interviewer may provide a provider-specific structured-output feature, partial streaming, or a nondeterministic regression.
