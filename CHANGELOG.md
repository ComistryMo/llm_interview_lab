# Changelog

本项目使用 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 风格，并遵循语义化版本。

## [Unreleased]

### Added

- 38 道原创 ready 固定题与 188 个 planned Catalog 节点；
- 12 条岗位 Track、11 条 Quest、8 个 planned Capstone；
- repository-local 多 Profile Workspace 与 append-only event reducer；
- `start → test → submit → review → D+2 → D+7 → mastered` CLI 闭环；
- 统一 submission loader、pytest 子进程、超时、输出截断与 SHA-256 证据；
- 固定 commit 的外部参考兼容清单与许可证审计。

### Changed

- 固定课程事实源收敛为 `curriculum/catalog/*.yaml`；
- 个人学习历史事实源收敛为每个 Profile 的 `events.jsonl`；
- README、架构、Workspace、出题规范和 AI 教练边界收敛为少量维护文档。

### Removed

- 公共维护者答案、状态、review、progress 与 handoff fixture；
- 重复的 Markdown 状态、旧 JSON Catalog、旧导航和被 CLI 替代的脚本。

## [0.1.0] - 2026-08-26

### Added

- Stage 00 训练原型；
- Python 3.10+ 环境检查和分层 pytest 入口；
- 精确时间语义的任务 ledger 与状态校验；
- fail-closed handoff 导出器；
- 无答案私人 workspace 生成器；
- 公共文档、治理文件和跨平台 CI。

[Unreleased]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.1.0
