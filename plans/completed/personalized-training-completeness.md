# Personalized Training Completeness

## Goal and observable outcome

Complete the existing three-entry product without adding a second state system:

- Personal Workspace stores structured career intent and explicitly registered resume, JD,
  internship, project, paper, competition, and real-interview-question evidence.
- Practice exposes difficulty, Quest-guided navigation, one-main-task enforcement, a
  derived mistake notebook, and a genuinely masterable Softmax-to-Attention path.
- Mock Interview keeps its frozen local session, but improves auditable personalized
  question delivery, candidate discovery, and report evidence.
- Repo-aware AI receives a deterministic, bounded, current-scope context instead of
  rereading full Catalog shards, event history, old submissions, or future questions.

The observable result is a clean clone in which a learner can use Practice alone, or
configure a local career profile and run a tailored interview with a BYO AI. No model
provider, server, database, telemetry, or runtime multi-agent system is introduced.

## Current repository facts

- Branch: `feature/career-interview-workspace`; baseline worktree is clean.
- Python: 3.11.9.
- Baseline: `261 passed, 9 skipped`; skips are Windows symlink-privilege cases.
- Doctor: 41 ready, 188 planned, 32 Oracle, 23 retention-ready, DAG valid.
- Canonical facts remain: Catalog shards, `profile.yaml`, Practice `events.jsonl`, material
  manifest, and one mock-interview `session.json` per interview.
- D+2 and D+7 are the current verified mastery gates. D+5 is not represented by verified
  public assets and will not be faked by reusing a starter or relabeling D+7.

## Scope and explicit non-goals

In scope:

1. Optional structured `career_intent` in the existing Profile, with an atomic CLI update.
2. Specific material kinds for career evidence and sanitized real interview questions.
3. Practice difficulty display, Quest navigation, one unfinished primary task, and a
   mistake view derived only from Practice events.
4. A deterministic, read-only, size-bounded AI context command for COACH, TEACHER,
   REVIEWER, and INTERVIEWER modes.
5. Minimal interview candidate discovery, pre-answer question delivery evidence, and
   complete objective evidence in reports.
6. The missing verified ATT-002 D+2/D+7 path needed to make the attention sequence
   masterable.
7. Focused documentation and regression tests.

Out of scope:

- Built-in model API clients, provider abstractions, Web/TUI, database, telemetry,
  remote accounts, multi-agent runtime, malicious-code sandboxing, or automatic mastery.
- Scanning a Profile, automatically uploading materials, or reading material bodies
  without explicit IDs and per-interview consent.
- A fabricated D+5 mastery stage without an independently authored and Oracle-validated
  variant. The product will state the verified default schedule as D+2/D+7.
- New planned curriculum nodes or broad course expansion.

## Milestones and validation

### 1. Career facts and materials

- Extend the Profile schema/template with bounded career intent.
- Add an atomic `profile configure` path and JSON profile view.
- Extend material kinds without changing the manifest fact model.
- Tests: profile/schema/material focused tests.

### 2. Practice navigation and evidence views

- Add pure event reduction for mistake summaries.
- Expose `mistakes`, difficulty, and Quest-aware `next`/`graph` views.
- Prevent a second unfinished base task from hiding the first.
- Repair the visible Transformer Quest sequence and ATT-002 retention gap.
- Tests: CLI, workspace, Catalog/DAG, ATT-002 public retention validation.

### 3. Minimal AI context

- Emit deterministic JSON with repo-relative paths, fingerprints, current-only state,
  an explicit read allowlist, and an 8 KiB hard limit.
- Slice exactly one requested H1-H3 section; never export H4/H5, raw events, answer bodies,
  public/private test source, future tasks, or future interview prompts.
- Tests: determinism, Profile isolation, read-only behavior, leakage guards, and size.

### 4. Mock-interview auditability

- List eligible Catalog candidates with current Practice status for AI-assisted planning.
- Record the exact delivered current question before the answer while keeping the existing
  `--asked-file` path compatible.
- Include configuration, selected problem, question record, and objective grader evidence
  in the generated report without copying answer or material bodies.
- Tests: ordering, immutability, report completeness, and Practice isolation.

### 5. Integrated documentation and verification

- Update README, Workspace/interview docs, AGENTS, and Coach Policy only where behavior
  changed; point AI onboarding at the bounded context command.
- Run focused suites, full pytest, doctor, CLI smoke tests, Git-ignore verification, and
  confirm no real Profile is tracked.

## Risks, rollback, and stop conditions

- Profile/session schema additions remain backward compatible; old Profiles and sessions
  must load unchanged. Roll back logical commits rather than rewriting history.
- Question delivery is additive; existing `interview answer --asked-file` remains valid.
- Material kind expansion does not move or rewrite existing private files.
- ATT-002 public retention assets contain no solution; Oracle implementations remain in
  ignored maintainer storage and are never tracked.
- Stop if a change would delete or expose Profile data, require history rewriting, or
  require a breaking CLI change.

## Decision log

- Reuse the existing canonical sources; derived mistake/context/report views are not stored
  as new facts.
- Keep BYO AI and explicit consent. "AI integration" means a deterministic local handoff,
  not a bundled remote model client.
- Keep D+2/D+7 as verified mastery gates. A requested D+5-like interval must eventually
  receive its own independent assets and migration; it is not emulated in this change.
- Quest order is guidance; prerequisites remain the hard DAG.

## Progress

- [x] Baseline and focused read-only audit.
- [x] Career facts and material taxonomy.
- [x] Practice navigation, mistakes, and ATT-002 retention.
- [x] Minimal AI context.
- [x] Mock-interview auditability.
- [x] Documentation and full verification.

## Final review

Completed on 2026-08-27.

- Repository Health: 299 passed, 11 skipped. Every skip is a Windows test that
  requires symlink privileges; link/reparse rejection also has privilege-free coverage.
- Catalog doctor: 41 ready, 188 planned, 32 Oracle, 24 retention-ready, DAG valid.
- ATT-002 D+2 Oracle: 14 public + 5 private tests passed.
- ATT-002 D+7 Oracle: 12 public + 6 private tests passed.
- `pytest --collect-only`: 310 repository-health nodes; curriculum starters and local
  Profile submissions remain outside root collection.
- Catalog Schema, shards, Problem assets, retention assets, Policy/context refs, and
  interview evidence all reject linked or reparse components before reading.
- Git privacy: only `workspace/profiles/.gitkeep` is tracked, while representative
  events, material, interview, and submission paths are ignored.
- Intentional limits: BYO AI only (no bundled model client); verified retention remains
  D+2/D+7, and no D+5 asset or mastery gate is claimed.
