<p align="center">
  <img src="src/llm_interview_lab/desktop/resources/app-icon.png" width="80" height="80" alt="LLM Interview Lab">
</p>

# LLM Interview Lab

[简体中文](README.md) | English

**Practice the code. Explain your projects. Rehearse the interview.**

LLM Interview Lab is a desktop practice tool for AI job candidates. Work through coding problems on your own, or bring your résumé and target role to an AI interview that follows your answers one question at a time.

The [Chinese README](README.md) is the canonical version. The application defaults to Chinese, with English available in settings and problem statements.

[Download](#download) · [Get started](#get-started) · [Documentation](docs/README.md) · [Feedback](https://github.com/ComistryMo/llm_interview_lab/issues)

![Desktop home, using sample data](docs/images/candidate-20260909/after/home-dark.png)

## Download

**v1.0.0 · Previous published installers** — for current prerelease changes, [run from source](#run-from-source).

| System | Download |
|---|---|
| Windows 10 / 11, x64 | [Portable ZIP](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-Windows-x64-portable.zip) — extract the entire folder and run `LLMInterviewLab.exe` |
| macOS 14+, Apple Silicon | [DMG](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.dmg) — open and drag the app into Applications |

Python is included. Do not move the Windows exe out of its folder. There is no Intel Mac build.

[Release notes](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0) · [Alternative macOS ZIP](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.app.zip) · [Checksums](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/SHA256SUMS.txt)

The packages do not have commercial code signing; the macOS app has no Apple Developer ID or notarization. Follow the [Windows](docs/windows.md) / [macOS](docs/macos.md) guide to verify the download before opening it.

## What you can practice

### An interview grounded in your experience

Introduction → experience deep dive → role fundamentals → coding → review.

The interviewer uses your authorized résumé, JD and previous answers to generate only the next question. Submit once to save your answer and continue. Pause, resume and retry are supported; AI generation time is excluded from your answering time.

Your role determines the focus. Easy, standard and hard change depth, breadth and pressure—not grading leniency. New interviews do not divide candidates into internship, graduate or experienced tiers.

Connect your own DeepSeek or OpenAI-compatible API, local Ollama, or an installed and signed-in Codex. Choose the model and supported reasoning settings in AI Connections or Codex settings.

### Code and fundamentals, together

Practice optimizers, stable losses, backpropagation, RMSNorm, MHA, RoPE, GQA, KV Cache, LoRA, SFT masking, DPO, GRPO and GAE. Knowledge cards connect concepts, derivations, common mistakes and follow-up questions to coding exercises.

Write your implementation and your own examples, then run them locally. Public tests are a separate action. AI feedback on your code does not mean an unexecuted program passed tests. Some exercises have prerequisites or need PyTorch; see the [content coverage](docs/content/release-candidate-coverage-20260909.zh.md).

### A useful next step after each attempt

Review the interview transcript, strengths, gaps and suggested practice. Assessments reference your actual answers or code; missing evidence remains visible. Practice progress and interview scores are separate. Passing public tests alone does not establish mastery.

Eight role areas cover AI product, applications, agents, algorithm research, post-training, ML infrastructure, inference systems, and evaluation/data safety. [Role details](docs/role-profiles.md).

## Get started

1. Create a local learning profile and choose a target role. You can practice without AI; the last profile is restored on startup.
2. For mock interviews, save your AI connection and model. Optionally import a redacted résumé or JD in Materials. Text-based PDF, DOCX and text files are supported; scanned PDFs need prior text extraction.
3. Choose difficulty and duration, confirm what this interview may send, and start answering. Settings and material selections are remembered, but a new interview still needs confirmation of its sending scope.

The first interview defaults to standard difficulty and 60 minutes. [Interview guide](docs/interviews.md).

## Speak your answers

Speech recognition runs locally, with no speech API key or cloud transcription charge.

In the interview answer area, select voice input, open voice settings and choose **Download local models**. The app downloads, verifies and installs about **1.19 GB** of weights; no manual extraction or path configuration is needed. Recognition can then work offline.

Text appears while you speak and is corrected after pauses. Finish recording, check the editable transcript, then submit. Initial loading can take longer; terminology, accents and noise can still cause errors. Downloads require access to the model sources. [Local speech guide](docs/local-stt.md).

## Costs, privacy and limits

- Local practice and speech recognition need no paid service. Cloud interview APIs use your own account and may incur provider charges; the project supplies no cloud quota. Ollama can run a local model.
- Profiles, materials, answers and recordings are stored locally. Remote interviewers receive confirmed context and answers you submit; this does not automatically upload local audio.
- API keys stay in the OS keyring and can be reused, changed or deleted. See [AI connections](docs/ai-connections.md) and [data management](docs/workspace.md). Do not import confidential employer materials.
- Run only code you trust. Local execution is not a hostile-code security sandbox.
- PyTorch is not bundled. DeepSeek high-reasoning requests have known empty-response or transport failures. Speech accuracy, latency and device compatibility vary. See [release limitations](docs/release-notes-v1.0.0.md).

## Run from source

**Active development is an early source prerelease (`1.0.1a1`), not a stable release.** No new installers are built this round. The existing v1.0.0 downloads do not include these changes. See [prerelease notes](docs/release-notes-v1.0.1-alpha.1.md). Python **3.11** is recommended.

~~~bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
~~~

Windows PowerShell (prepare once, then run):

~~~powershell
py -3.11 scripts/run_desktop.py --setup
.\.venv\Scripts\python.exe scripts/run_desktop.py
~~~

macOS/Linux:

~~~bash
python3.11 scripts/run_desktop.py --setup
.venv/bin/python scripts/run_desktop.py
~~~

After Python/QML edits, save and restart. No executable compilation, environment activation or manual `PYTHONPATH` is needed. Run `--setup` again only when dependencies change. The default data directory is `workspace/maintainer/manual-uat`; existing data and explicit environment overrides are preserved. Use `--data-root` for another directory. Normal launches do not install dependencies or modify Git sources.

For PyTorch exercises, install `-e ".[torch,dev]"` with the virtual environment's Python. Speech weights remain an optional in-app download.

[Source launch and data directory options](docs/desktop-app.md#源码运行)

## Documentation and feedback

[User guides](docs/README.md) · [Changelog](CHANGELOG.md) · [Report a problem](https://github.com/ComistryMo/llm_interview_lab/issues) · [Contribute](CONTRIBUTING.md)

Please redact screenshots and logs. Do not post API keys, complete résumés or private learning profiles.

[Apache-2.0](LICENSE) · [Third-party notices](docs/third-party-notices.md)
