# Windows Desktop App

The desktop Alpha is the recommended entry point for learners who want one
window for career materials, Practice, mock interviews, progress, and optional
AI. It is a native Qt Quick application built on the same Python services as the
CLI; it does not call the CLI or parse terminal output for ordinary operations.

## Choose an installation

### Portable Windows Alpha

1. Download `llm-interview-lab-windows-x64.zip` from the matching prerelease.
2. Extract the archive to a normal user-writable folder.
3. Run `LLMInterviewLab.exe`.

The portable app seeds public curriculum assets under
`%LOCALAPPDATA%\LLMInterviewLab` and keeps Profiles there. On an upgrade it
replaces public assets only. It never copies, scans, removes, or migrates
`workspace/profiles/` automatically.

The first portable Alpha intentionally omits CPU PyTorch to keep the executable
small enough to download and validate. It supports onboarding, career materials,
role interviews, AI connections, and Foundation exercises. Use a source install
for Tensor, optimizer, Transformer, and post-training coding exercises.

### Source install — full feature set

Use Python 3.11 on Windows:

```powershell
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[desktop,ai,torch,dev]"
llm-lab-gui
```

No AI connection is required. To omit provider libraries, install
`.[desktop,torch,dev]` instead.

## Four-step onboarding

1. **Profile** — enter a local ID such as `default`.
2. **Role** — choose one of eight Role Profiles.
3. **Self-assessment** — rate only the most relevant Skills from 0 to 4, or skip.
4. **AI** — keep the default **Use without AI**, connect a provider, or connect
   Codex later.

Self-assessment influences readiness views and recommendations. It is not
verified evidence and never unlocks a Problem or grants mastery.

## Pages

### Home

Home has one primary action: **Continue**. It summarizes the current Role,
current Practice task, pending Review/Retention, mastered count, recommended
Quests, last interview, and AI connection state. The full DAG is deliberately
not shown here.

### Career profile

Add a single, user-owned, sanitized material at a time. The app copies it into
the current ignored Profile and records its kind, title, size, relative path,
SHA-256, and whether it may be considered for AI consent. It never recursively
scans a resume directory.

Supported categories include resume, career intent, internship, project, paper,
competition, interview question, job description, portfolio, research, and
other. Text intended for AI should be UTF-8 Markdown or plain text. PDF/DOCX may
be archived locally but are opaque in this Alpha.

### Learn

The default view shows the Role path and recommended Quest cards. Each Problem
shows difficulty, asset status, validation level, prerequisites, retention
availability, and lock state. Experimental contract-only nodes are visible in
the advanced Catalog but are not recommended by default.

### Exercise Workspace

The screen keeps four concerns visible without mixing their authority:

- task contract and prerequisites;
- the current `submission.py`, saved atomically;
- public test output from the isolated grader subprocess;
- Review, D+2/D+7, and an optional AI Coach drawer.

Use **Save → Test → Submit → Review**. A Review requires an explanation,
complexity, boundary conditions, contract result, and oral result. D+2/D+7 can
start only when deterministic lifecycle rules permit them. Each retention stage
creates a new attempt and does not copy the old answer.

The editor is intentionally modest; it is not an IDE replacement. For complex
work, edit the printed/Profile path in VS Code and use the desktop app for task,
test, lifecycle, and AI context.

### Interview

Choose Role, seniority, difficulty, AI mode, and optionally exactly one
consented material. Starting a session freezes its Blueprint, question text,
rubric, material ID/SHA, seed, and deadline.

Only one main question is visible at a time. Non-coding rounds record an answer
and evidence-backed rubric assessment. Coding rounds expose a session-local
starter and run the normal grader; they never reuse a Practice submission.
Adaptive AI follow-up is archived under the current main question and does not
alter the frozen plan.

Finishing produces a Profile-local report with completion state, overall score,
Skill scores, question evidence, confidence, fatal issues, gaps, and uncertainty.
Missing rounds stay zero/unscored; the report is never re-normalized to look
better and never estimates an offer probability.

### AI Coach

Preview the exact context before sending. Practice modes are COACH, TEACHER
(H1/H2/H3), and REVIEWER. Interviewer mode is bound to the frozen current
question. Repository Agent mode is for maintainers and requires explicit Codex
approval for proposed writes/commands.

### Progress

Progress separates self-reported and verified Skill evidence. It shows mastered
Problems, Quest progress, retention due, help-level usage, and local interview
scores. Contract-only Problems and interview scores do not count as mastery.

### Connections and Settings

Connections manages no-AI, provider, and Codex modes. Provider metadata is
Profile-local; secrets use the system keyring. Settings controls light/dark/system
theme and font scale. The app restores non-sensitive UI preferences on restart.

## Recommended daily workflow

1. Open Home and follow **Continue** rather than browsing the whole Catalog.
2. Complete one primary Practice task; do due retention before new content.
3. Run tests locally before asking AI for help.
4. Use the lowest sufficient help level and keep the Context Preview small.
5. Submit only when the current SHA has passing evidence.
6. Complete Contract + Oral Review in your own words.
7. Run a role interview weekly; use its weakest cited Skills to choose the next
   Quest, not as mastery evidence.
8. Back up the ignored Profile to a private encrypted location.

## Accessibility and keyboard use

- Windows 125% and 150% scaling are supported through Qt high-DPI handling.
- Tab and Shift+Tab traverse controls; Enter/Space activate focused buttons.
- Focus and status use text/borders in addition to color.
- Font scale is adjustable from 85% to 140%.
- Long task text, code, transcripts, and output are scrollable.
- Minimum window size is 1080×680; 1280×800 or larger is recommended.

## Troubleshooting

### The app starts but a PyTorch exercise cannot import torch

The portable Alpha does not bundle PyTorch. Use the source install with
`.[desktop,torch,dev]`.

### Codex shows “Not found”

Install and authenticate the Codex CLI through its official instructions, then
restart the desktop app. The workbench launches `codex app-server --listen
stdio://`; it does not scrape the interactive terminal.

### A provider key cannot be saved

Confirm the operating-system keyring is available and the `ai` extra is
installed. The app deliberately refuses to fall back to a plaintext key file.

### A remote provider call fails

Use **Test Connection**. Authentication, rate-limit, timeout, and server errors
are sanitized so secrets are not echoed. Confirm model ID and endpoint; custom
endpoints are accepted only for OpenAI-compatible and Ollama connections.

The portable Alpha bundles OpenAI-compatible support (including Ollama's `/v1`
endpoint). Run the source installation with `.[desktop,ai,dev]` when native
Anthropic or Gemini protocol support is required.

### The local grader hangs

The grader has per-Problem time and output limits and runs in a child process.
It is not a security sandbox; only run code you trust.

## Development and packaging

```powershell
python -m pip install -e ".[desktop,ai,dev]"
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/infrastructure/test_desktop.py -q
Remove-Item Env:QT_QPA_PLATFORM
pyside6-deploy -c scripts/pysidedeploy.spec -f
python scripts/check_desktop_artifact.py `
  dist/desktop/LLMInterviewLab.exe `
  --report desktop-nuitka-report.xml
```

The release checker launches a fresh standalone instance using a temporary
`LOCALAPPDATA`, verifies a real rendered window screenshot, checks the version,
rejects private/oracle paths in the build report, and verifies that no Profile is
packaged or created during smoke startup.

Windows CI builds only on Python 3.11. The normal cross-platform matrix does not
install PySide6 or provider SDKs. Installer, code signing, automatic update, and
store distribution are later work.
