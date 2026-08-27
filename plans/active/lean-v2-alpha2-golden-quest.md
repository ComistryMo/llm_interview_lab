# LEAN-V2 Alpha.2 Golden Quest & Field Validation

## Goal and observable result

Ship one honest, end-to-end `Python Data Reliability` path: FND-001 through
FND-006 can each reach `mastered`, then unlock the runnable
`CAP-FND-001 Hard Sample Data Pipeline`. Default planning excludes
contract-only content, Oracle evidence is content-fingerprinted, and real Beta
runs can be recorded locally without collecting identity or submissions.

## Baseline

- `main` starts at `v0.2.0-alpha.1` (`5181c41`).
- Python 3.11.9 repository health: 136 passed, 2 Windows privilege skips.
- 38 ready, 13 Oracle-validated, 8 retention-ready, 188 planned, 0 field runs.
- Real profiles and maintainer Oracle material are ignored by Git.

## Scope and non-goals

- Add no planned nodes, tracks, top-level directories, telemetry, model API,
  Web/database/server, multi-Agent runtime, external course, event locking, or
  profile export.
- Do not rewrite history or track any real Profile or reference solution.
- Limit production changes to the existing Catalog, Workspace, CLI, and
  maintainer validation script; add only the requested field-run script.
- The required Capstone is the only new runnable curriculum asset.

## Milestones

1. Add validation fingerprints and the default quality gate; test stale
   evidence, experimental opt-in, display markers, and Profile isolation.
2. Make FND-001..006 a strict Quest chain, add and Oracle-validate missing base
   and D+2/D+7 evidence, and implement CAP-FND-001.
3. Add anonymous local field-run recording, Beta guide/form, honest README and
   Alpha.2 version metadata.
4. Run targeted tests, complete repository health, clean-clone Golden Quest
   E2E, remote CI, merge, and prerelease `v0.2.0-alpha.2`.

## Validation commands

```text
python scripts/validate_oracle.py <problem-id> [--stage d2|d7]
python -m pytest tests/infrastructure -q
python -m pytest --collect-only -q
python -m pytest -q
llm-lab doctor
python scripts/validate_external_courses.py
```

## Risks, rollback, and stop conditions

- Fingerprints intentionally make stale Oracle metadata fail closed; every
  pre-existing Oracle node must be revalidated before the branch is releasable.
- Ignored maintainer evidence is backed up by Git exclusion, not committed.
- Roll back logical commits with `git revert`; never force-push or rewrite
  history. Stop only for threatened Profile loss, history rewrite, or a major
  incompatible public API decision.

## Decision log

- Model `CAP-FND-001` as a runnable ProblemNode with six mastered
  prerequisites. This reuses the existing start/test/submit/review machinery
  and avoids a second capstone execution subsystem.
- A validation fingerprint excludes mutable maturity counters but includes the
  full runnable contract and all base/retention assets.
- Fingerprint mismatch is a repository-health failure, not an automatic file
  mutation.
- Automated E2E remains test evidence only; `field_runs` stays zero until a
  real external learner report is recorded.

## Progress

- [x] Baseline confirmed.
- [ ] Quality gate and fingerprint implemented.
- [ ] Golden Quest and Capstone Oracle-validated.
- [ ] Beta/field workflow documented and tested.
- [ ] Local and remote release gates passed.

