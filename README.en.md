# LLM Interview Lab

[简体中文（规范版本）](README.md) | English

> This is the English translation for v0.4.0-alpha.3. The Chinese documentation is canonical when wording differs.

A local-first, role-aware, AI-assisted interview workbench. It combines role skill maps, structured mock interviews, tested coding exercises, oral review, and spaced retention so that “I understand it” can become “I can implement and explain it independently.”

[![CI](https://github.com/ComistryMo/llm_interview_lab/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ComistryMo/llm_interview_lab/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ComistryMo/llm_interview_lab?include_prereleases)](https://github.com/ComistryMo/llm_interview_lab/releases)
[![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/github/license/ComistryMo/llm_interview_lab)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](#status)

[Download](#download) · [CLI quick start](#cli-quick-start) · [Connect AI](#optional-ai-connections)

![Desktop home](docs/images/desktop-home.png)

**Role-aware paths · Tested exercises · Structured interviews · AI coaching · Retention**

This is not a random question list, a one-pass mastery badge, or a way for AI to silently write a learner's answer. No AI connection is required.

## What it includes

- A private local Profile for career materials, submissions, interview records, and progress.
- Eight public Role Profiles for product, applied AI, agents, algorithms, post-training, infrastructure, inference, and evaluation/safety.
- A deterministic curriculum DAG, recommended Quests, and integration Capstones.
- Timed, structured mock interviews with evidence-backed scorecards.
- Public tests, contract review, oral defense, and D+2 / D+7 retention.
- Optional OpenAI-compatible, Ollama, and Codex connections with Context Preview and system-keyring credentials.

## Download

Release: [v0.4.0-alpha.3](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.3)

| User | Artifact |
|---|---|
| Windows 10/11 x64 | `LLMInterviewLab-Windows-x64-portable.zip` |
| Windows single file | `LLMInterviewLab-Windows-x64.exe` |
| Apple Silicon Mac, macOS 12+ | `LLMInterviewLab-macOS-arm64.dmg` |
| Apple Silicon automation/direct extraction | `LLMInterviewLab-macOS-arm64.app.zip` |
| Intel Mac | No verified Alpha.3 artifact |
| Developer or contributor | Source installation below |

The macOS Alpha is ad-hoc signed, not signed with an Apple Developer ID, and not notarized. Verify `SHA256SUMS.txt`; see the canonical [macOS guide](docs/macos.md). The Windows Alpha is also unsigned; see the [Windows guide](docs/windows.md).

First launch is intentionally short:

```text
Open the app
→ Create a Profile
→ Select a target role
→ Keep No AI, or connect AI
→ Start training
```

## CLI quick start

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
```

Activate `.venv` (`.venv\Scripts\Activate.ps1` on PowerShell or `. .venv/bin/activate` on macOS/Linux), then:

```bash
python -m pip install -e ".[dev]"
llm-lab init --profile default --track ai_foundation
llm-lab doctor
llm-lab next --profile default
llm-lab start FND-001 --profile default
llm-lab test FND-001 --profile default
```

The public starter is expected to fail until you implement it. PyTorch exercises use `python -m pip install -e ".[torch,dev]"`; the full desktop source build uses `.[desktop,ai,dev]`.

## Learning and interviews

```mermaid
flowchart LR
    A[Select role or track] --> B[Solve or interview]
    B --> C[Public evidence]
    C --> D[Review]
    D --> E[D+2]
    E --> F[D+7]
    F --> G[Mastered]
    G --> H[Unlock / Capstone]
```

**Public tests passed does not mean mastered.** AI cannot create objective test results or grant mastery. Mock-interview scores remain separate from Practice evidence.

## Optional AI connections

Choose one of three modes:

- **No AI:** local curriculum, grader, retention, and manual interviews still work.
- **Chat provider:** OpenAI, OpenAI-compatible endpoints, and Ollama are the packaged Alpha path. The source package also includes native Anthropic and Gemini adapters.
- **Codex:** official App Server integration for repository context, test execution, streamed events, diffs, and explicit approvals. It does not scrape terminal ANSI output.

Only fields selected in Context Preview are sent. API keys are stored in Windows Credential Manager or macOS Keychain and are never written to Profile YAML or events. Do not upload an entire Profile or confidential employer material.

## Data and privacy

- Source/CLI mode uses repository-local `workspace/profiles/<id>/`, ignored by Git.
- Packaged Windows uses `%LOCALAPPDATA%\LLM Interview Lab\`.
- Packaged macOS uses `~/Library/Application Support/LLM Interview Lab/`.
- The project has no account, cloud sync, or automatic telemetry.
- The local grader executes code you trust; it is not a hostile-code security sandbox.

## Status

As of v0.4.0-alpha.3: **42 Ready**, **187 Planned**, **33 Oracle-validated**, **24 Retention-ready**, **0 Field-tested runs**, **70 skills**, **8 roles**, **24 interview blueprints**, and **26 fixed non-coding interview items**.

This is an Alpha. The Windows and macOS packages have automated build/smoke validation, but no real Field Run is claimed. Provider behavior varies by upstream service, and Apple Developer ID signing/notarization is not yet configured.

## Contributing and support

- Start with [CONTRIBUTING.md](CONTRIBUTING.md).
- Report reproducible bugs through [GitHub Issues](https://github.com/ComistryMo/llm_interview_lab/issues).
- Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).
- Detailed user documentation is Chinese-first under [`docs/`](docs/desktop-app.md).

The project is licensed under [Apache License 2.0](LICENSE).
