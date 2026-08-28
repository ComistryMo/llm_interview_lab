# Personal Workspace and Mock Interview ExecPlan

## 1. Goal and observable outcome

Extend the clone-first product from a practice-only lab into three explicit local spaces:

1. Personal Workspace for explicitly registered career materials.
2. Practice for the existing Catalog/DAG/mastery lifecycle.
3. Mock Interview for configurable, timed interviews that reuse validated Catalog problems and produce structured local reports.

The observable vertical slice is: initialize a Profile, add a synthetic resume note, create a tailored 60-minute interview, freeze one validated Catalog coding problem, start the timer, reveal one question at a time, record answers, run the existing grader, attach evidence-based assessor scores, finalize a deterministic overall score, and render a Markdown report. The same API also accepts 30/45/90 minutes and easy/medium/hard.

## 2. Current repository facts

- Fixed questions are sourced only from `curriculum/catalog/*.yaml`.
- Practice history and mastery are sourced only from each Profile's `events.jsonl`.
- The existing grader already provides subprocess isolation, timeout, output truncation, SHA binding, and a unified submission loader.
- Every real Profile is under ignored `workspace/profiles/<profile_id>/`; CI uses synthetic fixtures only.
- Baseline on Python 3.11: 165 passed, 2 skipped (Windows symlink privileges).

## 3. Scope and explicit non-goals

In scope:

- `materials/manifest.json` plus copied local files with SHA-256 and per-session consent.
- `interviews/<interview_id>/session.json` as the interview source of truth, interview-local coding submission, and generated `report.md`.
- Deterministic problem selection, timeboxes, objective grader evidence, fixed rubric aggregation, provenance, and report generation.
- Repo-aware BYO AI `INTERVIEWER` policy and one prompt.
- CLI and docs for the vertical flow.

Out of scope:

- Model API clients, Web/TUI, database, server, telemetry, remote uploads, proctoring, multi-Agent runtime, PDF/OCR parsing, concurrency locks, employment predictions, or changing Catalog/mastery schemas.
- Reading or migrating any existing real Profile. Older Profiles receive missing directories only when that Profile is explicitly used.
- Treating an interview score as practice evidence, retention, or mastery.

## 4. Design decisions

- Practice and Mock Interview are separate bounded lifecycles inside one Profile. Interviews never append practice events.
- `session.json` is the sole interview fact source; `report.md` is generated and replaceable.
- Coding questions must be `ready` and validation `oracle|field|stable`; learning prerequisites do not gate diagnostic interviews.
- A tailored session can reference only material IDs explicitly selected and consented for that session. The plan freezes each material SHA and problem fingerprint; drift blocks execution.
- Material content is untrusted evidence, never instructions. The CLI never recursively scans materials, follows links, executes attachments, or uploads anything.
- The fixed mixed rubric totals 100: coding correctness 30, reasoning/complexity 20, technical oral 20, project evidence 15, communication 10, time management 5. Objective and assessor evidence remain visibly separate.
- Missing required evidence yields `incomplete`; weights are not renormalized. Difficulty is context, not a hidden score multiplier.
- Local timeboxing is auditable practice, not tamper-proof proctoring or a security sandbox.

## 5. Milestones and tests

1. Workspace/materials
   - Add profile-local directories, material validation, copy, digest, list/show.
   - Run `python -m pytest tests/infrastructure/test_career_materials.py -q`.
2. Interview engine
   - Add selection, session lifecycle, timer, answer recording, grader reuse, scoring, and report.
   - Run `python -m pytest tests/infrastructure/test_mock_interviews.py -q`.
3. CLI and Agent contract
   - Add material/interview commands, `INTERVIEWER` mode, and focused docs.
   - Run `python -m pytest tests/infrastructure/test_mock_interview_cli.py -q`.
4. Repository validation
   - Run targeted tests, collect-only, full pytest, doctor, Git-ignore checks, and a synthetic clean-clone flow.

## 6. Risks, rollback, and stop conditions

- Privacy risk: ignored Git paths do not control external AI providers. Commands and docs require explicit material allowlists and per-session consent; reports store IDs/evidence summaries, not material bodies.
- Prompt injection risk: materials are data. Agents must ignore embedded instructions and never follow embedded links or paths.
- Scoring risk: AI/human rubric scores are subjective. Every score requires source, evidence, and confidence; deterministic test results are separate.
- Compatibility risk: existing practice commands and Profile files remain unchanged. Rollback is deletion/revert of the new modules, schemas, CLI wiring, tests, and docs; real ignored Profile data must never be deleted automatically.
- Stop only if implementation would require changing the public practice lifecycle, reading real Profile data, rewriting Git history, or changing Catalog/mastery semantics.

## 7. Decision log

- 2026-08-27: selected two new directly used modules (`materials.py`, `interviews.py`) instead of provider/plugin abstractions.
- 2026-08-27: selected independent interview sessions rather than extending practice events, preventing mastery pollution.
- 2026-08-27: selected copied opaque PDF/DOCX storage but AI-readable text only for the first version; no parser dependencies.
- 2026-08-27: selected deterministic fixed rubrics and generated Markdown reports; no AI-written numeric aggregation.

## 8. Progress

- [x] Read existing Workspace, Catalog, CLI, grader, lifecycle, tests, AI Policy, and docs.
- [x] Confirm Python 3.11 baseline and full Repository Health.
- [x] Implement Personal Workspace materials.
- [x] Implement Mock Interview lifecycle and scoring.
- [x] Wire CLI and AI policy.
- [x] Complete tests, docs, clean-clone verification, and commits.

## 9. Final retrospective

Implemented the three-space product without changing Catalog, Practice events,
or mastery semantics.  Personal materials are copied into an ignored,
profile-scoped manifest with explicit AI eligibility and per-session consent.
Mock interviews freeze a validated Catalog problem, difficulty, duration,
question schedule, material digests, and rubric; they then enforce a monotonic
local clock, one-question-at-a-time evidence, shared-grader coding facts,
evidence-bearing subjective scores, and generated local reports.

Release review found and closed four important edge cases: unrelated damaged
materials no longer affect an explicitly selected material; linked/reparse
Profile paths are rejected; post-deadline assessor work remains visible without
misreporting candidate time; and completed archives warn when material,
Catalog, answer, or submission evidence drifts.  Documentation now keeps all
draft answer/evidence examples inside ignored Profile cache paths and separates
metadata inspection from consent to read material bodies.

Validation on Python 3.11.9 collected 270 Repository Health tests and finished
with 261 passed / 9 skipped.  The skips are Windows symlink-creation cases for
an account without that privilege; equivalent fake-reparse tests execute on
Windows.  `llm-lab doctor` passes, `git diff --check` passes, and only
`workspace/profiles/.gitkeep` is tracked.
