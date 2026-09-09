# LLM Interview Lab

[简体中文（规范版本）](README.md) | English

The Chinese README is the canonical product description. This is the translation for **v0.4.0-alpha.4**, published on 2026-09-09.

A local-first desktop workspace for AI interview practice: Chinese coding problems, one-question-at-a-time interviews, authorized résumé/JD context, and evidence-based review.

## Download

[Release and notes](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.4) · [SHA-256 checksums](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/SHA256SUMS.txt)

| Platform | Asset |
|---|---|
| Windows 10/11 x64 | [LLMInterviewLab-Windows-x64-portable.zip](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/LLMInterviewLab-Windows-x64-portable.zip) |
| macOS 14+, Apple Silicon | [LLMInterviewLab-macOS-arm64.dmg](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/LLMInterviewLab-macOS-arm64.dmg) |
| macOS 14+, Apple Silicon, ZIP | [LLMInterviewLab-macOS-arm64.app.zip](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/LLMInterviewLab-macOS-arm64.app.zip) |

Extract the **entire** Windows archive and run LLMInterviewLab.exe; do not move the exe alone. Python is bundled. On macOS, drag the app into Applications.
This is an Alpha, not a stable release. macOS uses ad-hoc signing, without Apple Developer ID or notarization. No Intel/Universal2 package is provided. Verify origin and checksums before following the [Windows](docs/windows.md) or [macOS](docs/macos.md) guide.

## Start

Create a local profile, choose a role, and start practicing. AI is optional for local coding, tests and progress; personalized desktop interviews require your own AI connection.

![Chinese desktop, synthetic profile](docs/images/candidate-20260909/after/home-dark.png)

[Current screenshots](docs/design/desktop-candidate-20260909.zh.md) · [Verification and limits](docs/desktop-candidate-20260909-report.zh.md)

## Interviews and practice

- Eight roles share a skill graph. Role and authorized background determine focus; easy/standard/hard determines depth and pressure, not grading leniency. New interviews do not divide candidates by internship, graduate or experienced status.
- Introduction → experience deep dive → role fundamentals → coding → evidence review. Only the next question is generated; no full future question list is frozen at startup.
- Submit once to save and continue. AI waiting does not consume candidate time. Detailed scoring happens after finishing, with retry of failed items only.
- Coding IDs must resolve to verified, runnable local problems. Running a custom Python example is separate from public tests and AI code evaluation.
- Chinese problems contain full requirements with an English toggle. A native editor provides line numbers, highlighting, indentation, undo/redo and save status.
- Passing public tests does not mean mastery. Review, oral explanation and verified D+2/D+7 variants remain separate requirements.

## AI and speech

Use your own DeepSeek/OpenAI-compatible API, local Ollama or installed Codex. Models and reasoning settings are configurable; keys are stored in the OS keyring and can be updated or deleted. Connections restore on startup. API probes may incur a small provider charge; the project supplies no cloud quota.

Speech defaults to **local streaming preview with Qwen3-ASR 0.6B endpoint correction**. Model weights download separately; no speech API key is required. Performance and accuracy depend on hardware and input. Optional remote transcription requires explicit selection and consent.

Known issue: historical DeepSeek high-reasoning transport/empty-body failures remain unverified as resolved. This publication did not run new paid-model or microphone acceptance tests.

## Privacy and evidence

Profiles, materials, answers, recordings and interviews remain local and excluded from release assets. Material preferences can restore when SHA matches, but new sessions still confirm the sending scope; changed or revoked material is not silently reused. Never include employer-confidential information.

The local grader is not a hostile-code security sandbox. AI assessments do not grant Practice mastery or claim an unrun program passed tests.

The catalog has **96 ready nodes (84 Oracle-validated, 12 contract-only), 158 planned nodes, 24 retention-ready problems, 255 knowledge cards and 258 source records**; field-tested runs remain 0. Optional PyTorch is not bundled: **27 verified coding problems are runnable in the portable runtime**, not all ready problems.

Artifacts come unchanged from [verified CI source 4f93969](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34288557804). The release tag also includes documentation and archive organization, with unchanged application/build inputs. Windows native synthetic UAT passed; macOS 15 arm64 CI passed build, launch, worker and mounted-package checks. These are not physical-macOS, fresh-Windows-VM or live-microphone acceptance claims.

## Source installation

Python 3.11 is recommended; core CLI supports 3.10–3.12.

~~~bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
~~~

Activate the virtual environment (PowerShell: .venv\Scripts\Activate.ps1; macOS/Linux: . .venv/bin/activate), then:

~~~bash
python -m pip install -e ".[desktop,ai,dev]"
llm-lab-gui
~~~

For PyTorch problems, install the torch,dev extras. Keep application data when upgrading; the app can download and verify updates but will not silently install them.

[Chinese documentation](docs/README.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Plans and history](plans/README.md)
