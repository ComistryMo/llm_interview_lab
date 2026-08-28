# Changelog

Notable project changes are documented here using the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Release tags
follow semantic versioning and Alpha releases are not stable APIs.

## [Unreleased]

## [0.4.0-alpha.1] - 2026-08-28

### Added

- A canonical ontology of 70 skills across 16 domains, eight Role Profiles,
  seniority-aware Interview Blueprints, and 24 original non-coding interview
  items with evidence-based rubrics.
- A local-first PySide6 and Qt Quick Windows desktop workbench for onboarding,
  career materials, Practice, mock interviews, progress, settings, and AI
  connections.
- Optional OpenAI-compatible, OpenAI, Ollama, Anthropic, Gemini, and Codex
  connections with context preview, system-keyring credentials, and explicit
  Codex approvals.
- A role-aware `llm-lab quickstart` path and deterministic structured interview
  lifecycle shared by the CLI and desktop application.
- Windows portable packaging, GUI smoke tests, privacy inspection, five real
  application screenshots, and focused desktop/AI/role documentation.

### Changed

- Public positioning now describes a role-aware AI interview workbench rather
  than only an algorithm exercise repository.
- Profile path validation now reports symlink and reparse failures consistently
  across Windows and POSIX before invoking Git.

### Security

- Real Profiles, career materials, submissions, interview records, secrets,
  private tests, and maintainer oracles remain outside tracked release assets.
- Remote AI receives only the fields selected in Context Preview; API keys are
  referenced through the operating-system keyring rather than stored in YAML.

## [0.3.0-alpha.1] - 2026-08-27

### Added

- Continuous Tensor and Stable Loss and Optimizer and Training Loop Golden
  Quests, including two validated integration Capstones.
- A product-focused README with verified CLI onboarding and bounded BYO-AI
  guidance.

## [0.2.0-alpha.2] - 2026-08-27

### Added

- The first end-to-end Python Data Reliability Golden Quest and Capstone.
- Quality-aware planning, oracle fingerprints, deterministic retention assets,
  and a minimal anonymous field-validation record format.

## [0.2.0-alpha.1] - 2026-08-27

### Added

- The repository-local multi-Profile Workspace, Catalog/DAG validation, local
  grader, and `start -> test -> submit -> review -> retain -> mastered` CLI.
- Public curriculum validation levels, maintainer oracle validation, and the
  first retention-ready fixed exercises.

### Removed

- Tracked maintainer answers, personal state, reviews, progress, and handoff
  fixtures. Ignored local Profile data was preserved without rewriting history.

## [0.1.0] - 2026-08-26

### Added

- The Stage 00 training prototype, Python environment checks, scoped pytest
  entry points, privacy-oriented handoff export, and initial public governance.

[Unreleased]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.1...HEAD
[0.4.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.3.0-alpha.1...v0.4.0-alpha.1
[0.3.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.2...v0.3.0-alpha.1
[0.2.0-alpha.2]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.1...v0.2.0-alpha.2
[0.2.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.1.0...v0.2.0-alpha.1
[0.1.0]: https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.1.0
