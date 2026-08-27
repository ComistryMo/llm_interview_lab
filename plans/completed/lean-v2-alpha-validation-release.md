# LEAN-V2 Alpha Validation & Release Sprint

## Goal

Release an honest public Alpha without expanding course breadth: explicit validation maturity, ignored maintainer oracles, verified retention assets, hard-dependency DAG semantics, cross-platform CI, and a small beta-feedback entry.

## Scope boundaries

- Keep 38 ready and 188 planned nodes unchanged.
- Do not add top-level directories, public solutions, Web/database/multi-Agent systems, or external-course content.
- Keep real profiles and all oracle submissions/private tests ignored.
- Treat public tests as feedback and the grader as a trusted-local-code guardrail, not a sandbox.

## Evidence

- [x] All ready nodes have `validation.level` and `field_runs`; 13 are oracle-validated.
- [x] Eight problems have independent, oracle-validated D+2 and D+7 starter/test assets.
- [x] Problems without verified retention assets stop at `reviewed` and show `MASTERY BLOCKED`.
- [x] Optimizer, Attention/KV Cache, MQA/GQA, and Agent Loop hard dependencies were corrected.
- [x] Local collection: 137 repository-health tests; no course starter/retention/Profile collection.
- [x] Local regression: 135 passed, 2 Windows privilege skips.
- [x] README Alpha disclosure, beta issue form, and one Ubuntu 3.11 CPU PyTorch job are present.
- [x] Draft PR #1 created; push and pull-request CI each passed all seven jobs. Release gate approved for main merge and `v0.2.0-alpha.1`.

## Rollback

Each logical batch is reverted with `git revert <commit>`. No history rewrite, force push, or deletion of ignored profiles is part of this sprint.
