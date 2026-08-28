# INT-003 · Choose Prompting, RAG, or an Agent

## Scenario

A fictional operations team wants an assistant that answers policy questions and may eventually perform reversible workflow actions. Documentation changes weekly and source authority varies.

## Primary question

Choose an initial architecture among prompt-only generation, retrieval augmentation, deterministic workflow automation, and a tool-using agent. Explain the decision boundary, evaluation plan, permissions, fallback, and migration path.

## Constraints

- The first release must be useful without granting write access.
- Sources can conflict and may be stale.
- Do not treat “agent” as a synonym for every multi-step workflow.

## Follow-up axes

The interviewer may add a strict latency budget, an action requirement, or weak retrieval quality.
