# 变更日志

重要变更按 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 记录。版本号遵循语义化版本；Alpha 是预发布版本，公开接口仍可能调整。

## [未发布]

## [0.4.0-alpha.3] - 2026-08-29

### 修复

- 修复桌面端首次启动、岗位选择、最新答案测试与错误提示的可靠性；
- 练习页在窄窗口下改用真实的题面与 AI 教练入口，移除无法发送的假聊天控件；
- 启动诊断日志补充最小运行环境信息，并同步 Alpha.3 版本元数据。

## [0.4.0-alpha.2] - 2026-08-28

### 新增

- 中文成为 README、用户文档、社区模板和桌面界面的规范语言，并保留精简英文 README 作为翻译；
- macOS Apple Silicon 桌面构建：`.app.zip`、`.dmg`、应用 Bundle 元数据、原创 `.icns`、Ad-hoc Signing、架构检查、GUI Smoke 和隐私检查；
- 源码模式与打包桌面模式的统一数据位置解析：源码继续使用仓库内 `workspace/`，桌面应用使用系统应用数据目录；
- Finder 启动场景下的 Codex 常见路径探测和用户自选可执行文件；
- Windows / macOS 使用说明、术语表和中文文档契约测试。

### 改进

- 首次启动收敛为四步，默认“不连接 AI”；首页只保留“继续训练”和“开始模拟面试”两个主动作；
- AI 连接表单减少必填项，错误信息提供可执行的中文下一步；
- Provider 和 Codex 延迟探测，不阻塞首窗口和 No-AI 本地流程；
- 桌面端支持打开数据目录和日志目录；旧版 Windows 数据仅在用户确认后迁移，迁移前备份并校验 SHA-256；
- Windows Artifact 采用固定公开文件名，并与 macOS Artifact 一起接受解包后的隐私检查。

### 安全与发布状态

- API Key 继续只存入系统 Keyring；Keyring 不可用时不会回退到明文文件；
- 真实 Profile、求职材料、Submission、Transcript、Oracle、Private Tests、Secret 和 Git 历史不会进入桌面 Artifact；
- macOS Alpha 使用 Ad-hoc Signing，**未使用 Apple Developer ID 签名，也未经过 Apple Notarization**；
- 本版只发布经过 arm64 Runner 构建和启动验证的 Apple Silicon 包，不宣称 Intel Mac 或 Universal2 支持；
- 真实 Field Runs 仍为 0，不把自动化测试计作真实用户验证。

## [0.4.0-alpha.1] - 2026-08-28

### 新增

- 70 项规范技能、16 个技能域、8 个岗位画像、分级面试蓝图和 24 个带证据 Rubric 的原创非代码面试题；
- 基于 PySide6 / Qt Quick 的 Windows 本地桌面工作台，覆盖首次启动、求职材料、刷题、模拟面试、进度、设置和 AI 连接；
- OpenAI-compatible、OpenAI、Ollama、Anthropic、Gemini 与 Codex 可选连接，上下文预览、系统 Keyring 和 Codex 显式操作审批；
- `llm-lab quickstart` 与 CLI / GUI 共用的确定性面试生命周期；
- Windows Portable 打包、GUI Smoke、Artifact 隐私检查和五张真实界面截图。

### 调整

- 项目定位从算法手撕题库升级为岗位感知的本地 AI 面试训练工作台；
- Windows / POSIX 在调用 Git 前统一检查 Profile 的 symlink / reparse 边界。

## [0.3.0-alpha.1] - 2026-08-27

### 新增

- 可连续走通的 Tensor & Stable Loss、Optimizer & Training Loop 两条 Golden Quest，以及两个经过验证的综合关卡；
- 经过 clean-clone 验证的产品首页和受约束的 Bring Your Own AI 指南。

## [0.2.0-alpha.2] - 2026-08-27

### 新增

- 第一条端到端 Python Data Reliability Golden Quest 和综合关卡；
- 质量门槛、Oracle Fingerprint、确定性间隔复测资产和最小匿名 Field Validation 记录格式。

## [0.2.0-alpha.1] - 2026-08-27

### 新增

- 仓库内多学习档案个人工作区、Catalog / DAG 校验、本地 Grader 和 `start -> test -> submit -> review -> retain -> mastered` CLI；
- 课程验证等级、维护者 Oracle 验证和首批可复测固定题。

### 移除

- Git 跟踪的维护者答案、个人状态、Review、进度和 Handoff fixture；保留被忽略的本地档案，未重写历史。

## [0.1.0] - 2026-08-26

### 新增

- Stage 00 训练原型、Python 环境检查、限定 pytest 入口、隐私交接导出和初始开源治理。

[未发布]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.3...HEAD
[0.4.0-alpha.3]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.2...v0.4.0-alpha.3
[0.4.0-alpha.2]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.1...v0.4.0-alpha.2
[0.4.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.3.0-alpha.1...v0.4.0-alpha.1
[0.3.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.2...v0.3.0-alpha.1
[0.2.0-alpha.2]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.1...v0.2.0-alpha.2
[0.2.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.1.0...v0.2.0-alpha.1
[0.1.0]: https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.1.0
