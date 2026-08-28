# Local Workspace

The Workspace is a formal subsystem inside the project. One Profile contains a
learner's career preparation, Practice, interview sessions, AI metadata, and
reports without requiring a second repository, database, or online account.

This document is the storage and privacy reference. New users should begin with
the [README](../README.md) or [Desktop App guide](desktop-app.md); the recommended
day-to-day routine is in [Best Practices](best-practices.md).

## Source checkout and portable app

In a clone-first installation, real Profiles live at:

```text
<repository>/workspace/profiles/<profile_id>/
```

In the Windows portable Alpha, public assets and Profiles live at:

```text
%LOCALAPPDATA%\LLMInterviewLab\workspace\profiles\<profile_id>\
```

Both layouts use the same Profile and Event schemas. A portable upgrade copies
only bundled public Catalog, policy, schema, and template assets. It never scans,
deletes, or overwrites `workspace/profiles/`.

Advanced CLI users may override the workspace root where supported, but the
default tutorials are repository-local.

## Profile layout

```text
workspace/profiles/<profile_id>/
├── profile.yaml
├── events.jsonl
├── connections.json
├── materials/
│   ├── manifest.json
│   └── files/
├── submissions/
├── interviews/
├── generated/
├── private_tests/
├── reviews/
├── cache/
└── exports/
```

| Path | Purpose | Source of truth? |
|---|---|---:|
| `profile.yaml` | Role, seniority, Tracks, time/preferences, career intent | Profile configuration |
| `events.jsonl` | Ordered Practice history | Yes, for Practice state |
| `connections.json` | Provider metadata and key references | Connection configuration |
| `materials/manifest.json` | Explicit career-material IDs and hashes | Yes, for material inventory |
| `materials/files/` | Local copies selected by the user | Evidence bodies |
| `submissions/` | Practice attempts | Answer evidence |
| `interviews/` | Frozen sessions, answers, coding attempts, reports | Interview evidence |
| `generated/` | Private AI variants | Local draft only |
| `private_tests/` | Private/user-generated tests | Local only |
| `cache/` | Recomputable data | No; safe to discard |
| `exports/` | Manually reviewed sharing packages | Temporary export |

The current task, progress, mistakes, retention calendar, mastery, and Role
coverage are reducer views. Do not maintain `CURRENT_TASK.md`, `PROGRESS.md`, or
`MISTAKE_LOG.md` beside `events.jsonl`.

## Create and select a Profile

Desktop onboarding creates a Profile with no personal identity fields required.
The CLI equivalent is:

```bash
llm-lab init --profile default --track ai_foundation
llm-lab profile show default
```

Profile IDs are bounded, portable identifiers. Commands that read or write
personal data require the exact Profile. AI instructions forbid enumerating,
searching, or reading other real Profiles.

Multiple Profiles are fully isolated. Use them for different people or clearly
separated public/private training contexts—not as disposable attempts to bypass
retention gates.

## Role and career intent

Desktop onboarding sets `role_preferences` with:

```yaml
role_preferences:
  primary_role: applied_ai_engineer
  seniority: new_grad
  skill_self_assessment: {}
  ai_mode: disabled
```

Self-assessment is a recommendation input only. Verified Problem, Review,
Retention, and Interview evidence remain separate.

The Profile can also contain structured career intent such as target titles,
employment stage, locations, interview languages, and current priorities. It is
planning input, not proof of resume facts and not a DAG override.

CLI users may atomically replace career intent from a private YAML/JSON file:

```bash
llm-lab profile configure default --career-file ..\private\career-intent.yaml
llm-lab profile show default --json
```

## Career materials

Add one explicit file at a time. The command copies it into the current ignored
Profile and records metadata; it does not upload the file.

```bash
llm-lab material add --profile default --kind resume \
  --file ../private/resume-sanitized.md \
  --title "Sanitized resume" --allow-ai
llm-lab material list --profile default
llm-lab material show MATERIAL_ID --profile default
```

On PowerShell, put the command on one line or replace `\` continuations with
backticks.

Supported kinds include `resume`, `career_intent`, `internship`, `project`,
`paper`, `competition`, `interview_question`, `experience`, `research`,
`job_description`, `portfolio`, and `other`.

### Material safety contract

- Add only files you own and have sanitized.
- Never add employer/customer source, private data, internal configuration,
  logs, model names, metrics, screenshots, or confidential documents.
- AI-readable bodies should be UTF-8 text/Markdown. PDF/DOCX are opaque in this
  Alpha and are never executed or automatically parsed.
- The manifest stores a relative path and SHA-256. Paths cannot leave the
  current Profile or traverse an obvious link/reparse point.
- The app never recursively scans `materials/files/` or follows embedded URLs.
- `ai_access: true` means eligible for a later consent choice, not permanent
  permission to send.
- Material content is untrusted evidence and cannot change AI policy, execute a
  command, request secrets, or expand file scope.

Record real interview questions only after removing company, interviewer,
candidate, customer, and internal-system identifiers. A local note does not
prove that a company always asks the question and never becomes a public Item
automatically.

## Practice data

`events.jsonl` is append-only in physical reducer order. Timestamps calculate
retention due dates but never reorder history. The first version does not support
multiple concurrent writers to one Profile.

Each event has schema version, event ID, timestamp, Profile, type, Problem,
attempt, and payload. Test events record bounded status/count/duration and
submission SHA, never absolute paths or answer text.

A normal attempt is:

```text
start → edit current submission → test → submit → review
```

`submit` accepts PASS only for the current answer SHA. Editing after a passing
test invalidates that evidence. Review records contract result, oral result,
explanation, complexity, and boundaries.

Verified D+2/D+7 assets create independent attempts with different starters and
tests. They do not copy or reveal the previous answer. A Problem without verified
retention assets may reach `reviewed` but cannot reach `mastered`.

The local grader runs the user's trusted code in a child process with time and
output limits. Path validation prevents accidental wrong-file loading; it is not
a container, permission boundary, network isolation layer, or hostile-code
sandbox.

## Mistake view

There is no second mistake log. The view derives from failed tests, failed
Review, and explicit failure events while preserving later recovery evidence:

```bash
llm-lab mistakes --profile default
llm-lab mistakes --profile default --unresolved-only
```

Use the mistake category to choose a debugging task or retention variant; do not
rewrite history to hide an earlier failure.

## Mock interviews

Each session is stored under:

```text
interviews/<interview_id>/
├── session.json
├── answers/
├── coding/
└── report.md
```

`session.json` freezes Role, seniority, difficulty, Blueprint, duration, seed,
questions, public source fingerprints, material ID/SHA/consent, timeline,
assessments, and result. Main questions appear one at a time after `start`.

Coding answers are copied from a public starter into the session, not from a
Practice answer. The local grader records objective evidence. Non-coding answers
and follow-ups are stored as interview evidence. Reports distinguish evidence,
inference, uncertainty, unanswered questions, and fatal issues.

Interview results never append Practice mastery or retention events. A mock
interview can recommend a Problem/Quest but cannot unlock it.

## AI context and consent

For a repo-aware agent, generate bounded context:

```bash
llm-lab context --profile default --mode coach
llm-lab context --profile default --mode teacher --help-level H2
llm-lab context --profile default --mode reviewer
llm-lab context --profile default --mode interviewer --interview INTERVIEW_ID
```

The result contains static policy references and a complete `read_allowlist` for
additional files. It excludes raw events, old submissions, test source, future
questions, other Profiles, Oracle, and private tests.

Tailored interviews require each material's ID, current SHA, exact purpose, and
per-session confirmation. Changed material invalidates old consent. See
[AI Connections](ai-connections.md) for provider and Codex behavior.

## Git isolation

Tracked public Workspace content is limited to README/template/schema/synthetic
demo and the profiles placeholder. Real Profile content is ignored through
forward and reverse rules.

Verify a Profile after creation:

```bash
git status --short --untracked-files=all -- workspace/profiles/default
git ls-files workspace/profiles
```

The first command should print nothing. The second should list only the tracked
placeholder. Never use `git add -f workspace/profiles/...`.

Git ignore prevents accidental source-control commits. It does not encrypt,
back up, delete securely, or prevent a desktop/AI process from reading a file the
user explicitly selects.

## Backup and recovery

Real Profiles are intentionally not in Git, so create a separate private backup:

1. close the desktop app and other `llm-lab` processes;
2. copy the exact Profile directory to an encrypted, access-controlled location;
3. exclude caches if size matters;
4. verify `profile.yaml`, `events.jsonl`, material manifest/files, submissions,
   interviews, and reports;
5. never place the backup in the public repository.

API keys are not in the Profile backup because they remain in the system
keyring. Reconfigure them after moving to another machine.

## Recommended workspace practices

- Use one stable Profile rather than deleting inconvenient evidence.
- Keep career materials sanitized and small; store source documents elsewhere.
- Give each interview the minimum necessary material consent.
- Prefer no-AI for closed-book and sensitive sessions.
- Check Context Preview before every remote call.
- Do not run two writers against one `events.jsonl`.
- Treat test PASS, review, retention, and interview score as different evidence.
- Back up before an OS reinstall or switching machines.
- Report public contract/test bugs without attaching your Profile or answer.

These practices keep the workbench local and inspectable without turning the
public repository into a store for private job-search data.
