# All-AI Roles Desktop App ExecPlan

## 1. Goal and observable outcome

Upgrade the repository from an algorithm-oriented CLI into a local-first,
role-aware interview workbench without replacing its deterministic Practice
core. The release candidate must expose eight public role profiles, a canonical
skill ontology, structured interview blueprints and fixed non-coding items, a
shared Python application service, an optional PySide6/QML Windows desktop app,
BYO chat providers, a Codex App Server client, and a concise public onboarding
path. Existing CLI commands and ignored Profile data remain compatible.

Observable completion means the no-AI desktop path can create a Profile, select
a role, continue Practice, run a local test, and complete a structured interview;
provider and Codex paths pass fake-backed tests; Windows CI builds and launches
the executable; the README contains real screenshots and verified commands.

## 2. Current repository facts

- Starting point: clean `feature/career-interview-workspace` at `2c3f5cc`,
  branched to `feature/all-ai-roles-desktop-app`.
- Runtime gate: repository `.venv` uses Python 3.11.9. The system `python`
  command points to an unsupported/unprepared Python 3.9 and is not used.
- Baseline: 303 passed, 11 Windows privilege-related skips.
- Catalog: 41 ready, 188 planned, 32 Oracle, 24 retention-ready, 0 field runs;
  DAG, demo schema, and Profile Git isolation pass.
- Existing public objects: Problem, Track, Quest, Capstone, Profile and Events.
- Existing Profile-local systems: career material manifest, consent-by-ID/SHA,
  Practice submissions, retention, and timed coding-centric mock interviews.
- Current release on `main`: `v0.3.0-alpha.1`. The new feature branch preserves
  the newer Personal Workspace/Interview commits that have not yet reached main.

## 3. Scope and non-goals

In scope: 60+ canonical skills in 12+ domains; eight roles and aliases; role
blueprints for intern/new-grad/mid; 24+ original non-coding interview items with
rubrics; backward-compatible coding kind; deterministic role interview engine;
interactive `quickstart`; thin shared application service; optional PySide6/QML
desktop; no-AI path; optional any-llm providers and system keyring; official
Codex App Server JSONL client; context preview and approvals; docs, real
screenshots, Windows packaging, CI, PR and alpha prerelease when green.

Out of scope: database, server, Web UI, TUI, accounts, cloud sync, telemetry,
multi-agent runtime, model-hosting features, automatic mastery, automatic course
publishing, external course expansion, hidden-test claims, installer/store,
code-signing, auto-update, and broad rewrites of existing coding exercises.

## 4. Milestones

1. Public model: Skill/Role/Blueprint/InterviewItem loaders, schemas, validation,
   eight roles, 24 blueprints (three seniorities), 24 fixed items, and tests.
2. Interview vertical slice: deterministic fixed-item selection, one-question
   progression, evidence-based rubric scoring, Profile-local report, quickstart,
   and shared ApplicationService; preserve the existing interview CLI.
3. Desktop core: optional PySide6/QML shell, onboarding, Home, Learn, Exercise,
   Interview, Progress, Connections and Settings, all calling ApplicationService.
4. AI edges: provider protocol, any-llm adapter, mock/no-AI provider, keyring,
   bounded context preview, official Codex App Server JSONL client and approval
   state; never read a Profile or material outside explicit scope.
5. Product delivery: offscreen GUI tests and real screenshots, Windows deploy
   workflow/artifact, README and three focused docs, clean-clone and packaging
   checks, commits, PR, green CI, merge and a non-overwriting alpha tag.

## 5. Verification commands

- Model/content: `.venv\\Scripts\\python -m pytest tests/infrastructure/test_roles.py tests/infrastructure/test_role_interviews.py -q`
- Application/CLI: `.venv\\Scripts\\python -m pytest tests/infrastructure/test_application.py tests/infrastructure/test_quickstart.py -q`
- AI: `.venv\\Scripts\\python -m pytest tests/infrastructure/test_ai_connections.py -q`
- Desktop: `.venv\\Scripts\\python -m pytest tests/infrastructure/test_desktop.py -q` with
  `QT_QPA_PLATFORM=offscreen`.
- Repository health: `.venv\\Scripts\\python -m pytest -q` and
  `.venv\\Scripts\\llm-lab.exe doctor`.
- Build: Windows workflow runs the Qt deploy configuration, starts the artifact
  in smoke mode, checks version, and rejects Profile/oracle/secret payloads.

## 6. Risks, rollback and stop conditions

- PySide6 and any-llm remain optional extras, so core CLI installs stay small.
- any-llm requires Python 3.11; desktop/AI release builds therefore use 3.11,
  while the existing core Python 3.10 matrix remains supported.
- QML packages can be missed by Python packaging; explicit package-data and a
  packaged smoke test guard this.
- Codex integration uses the official App Server process and bidirectional
  JSONL protocol, never terminal scraping. Version/capability mismatch fails
  closed and leaves no-AI mode usable.
- Keyring failure must not fall back to plaintext secret storage.
- Existing Profile schemas are extended compatibly with defaults/migrations;
  no real Profile is enumerated, read, moved, or committed.
- Stop only for potential Profile/submission/oracle loss, history rewrite,
  unavoidable CLI breakage, license-changing dependency, or an irreconcilable
  public API direction.
- Rollback is commit-by-commit on this feature branch; no history rewrite. The
  starting commit is `2c3f5cc`.

## 7. Decision log

- 2026-08-28: branch from the latest clean feature HEAD rather than `main`,
  because the requested product depends on its already implemented Personal
  Workspace and Mock Interview features.
- 2026-08-28: use PySide6 + Qt Quick, optional at install time; GUI invokes a
  shared service, not CLI subprocesses.
- 2026-08-28: use Mozilla any-llm as the optional multi-provider adapter on
  Python 3.11+ (Apache-2.0), with no-AI as the default.
- 2026-08-28: use Codex App Server JSONL/stdio. Official guidance identifies it
  as the first-class rich-client surface with thread/turn/item and bidirectional
  approval events.
- 2026-08-28: retain legacy Problem `skills` tags and add canonical skill IDs
  compatibly; roles may only reference the canonical ontology.
- 2026-08-28: non-coding fixed items share one deterministic public loader and
  four-file asset contract; they do not masquerade as pytest Problems.
- 2026-08-28: keep `any-llm` as the source-install adapter for native Anthropic
  and Gemini protocols, but package a compact `httpx` OpenAI-compatible/Ollama
  adapter in the portable executable. Including every provider SDK made the
  Nuitka closure several thousand C files and was not viable for the Alpha.
- 2026-08-28: standalone builds seed only public Catalog, Problem, retention,
  schema and policy assets under `%LOCALAPPDATA%`; Profile directories remain
  empty until the local user initializes one. A standalone marker replaces Git
  ignore checks only outside a checkout and never weakens Profile path checks.
- 2026-08-28: explicitly include public `.py` starter/test assets in the deploy
  spec because Nuitka treats Python files as code and omits them from a generic
  data-directory include. The artifact smoke test catches this class of drift.

## 8. Progress

- [x] Recover Python 3.11 environment and run baseline.
- [x] Create feature branch and inspect public architecture.
- [x] Review requested README references and official Codex integration source.
- [x] Implement and test public role/skill/interview content model.
- [x] Implement and test interview/application vertical slice and quickstart.
- [x] Implement and test desktop application.
- [x] Implement and test AI connections and Codex backend.
- [x] Rewrite docs, capture real screenshots and verify packaging.
- [ ] Run local/remote CI, merge and publish alpha prerelease.

## 9. Final retrospective

Pending completion.
