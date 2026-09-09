# 变更日志

产品从 **v1.0.0** 开始正式发布。此前的 `0.x / Alpha` 是开发期编号，保留记录用于追溯，不作为对外产品代际。

## [未发布]

暂无未发布变更。

## [1.0.0] - 2026-09-09

### 首次正式发布

- 统一产品、源码、桌面包与下载入口的版本为 v1.0.0。
- 提供中文 Windows 与 macOS 桌面应用：逐问 AI 模拟面试、手撕与知识练习、材料管理、面试复盘和本地流式语音输入。
- README 重写为面向使用者的产品首页，同步英文版、安装指南和语音下载说明。
- 清理 GitHub 上的旧开发版 Release 页面与附件；保留 Git 提交与历史标签。清理前备份旧发布说明和文件。
- 正式版编号不代表已解决全部已知问题；签名、PyTorch、语音和高推理限制见[发布说明](docs/release-notes-v1.0.0.md)。

## 开发期记录

以下是 v1 之前的开发与验证历史，不是当前下载说明。

## [0.4.0-alpha.4] - 2026-09-09

### 桌面、面试与内容

- 公开发布中文 Windows x64 便携包与 macOS 14+ Apple Silicon DMG / APP ZIP；保留 Alpha 标记，不宣称稳定版或 Apple 公证。
- 统一深浅主题与输入控件、可收起侧栏、宽屏布局、完整中文题面；首页围绕面试、练习与复盘，独立 AI 辅助入口移除。
- 新动态面试取消求职阶段分档；岗位与授权经历决定方向，难度决定深度和广度。提交后逐问生成，AI 等待不扣候选时间，结束后台证据评分。
- 共享代码编辑器、自写样例运行与公开测试分开；非法手撕 ID 拒绝，未评分或未运行不冒充成功。
- 96 道 ready（84 Oracle、12 契约级）、158 planned、24 retention-ready、255 知识卡及 258 去重来源；便携包未内置 PyTorch，27 道已验证代码题具备运行环境。
- PDF/DOCX 文本快照、Profile 与上次配置恢复、材料 SHA 授权校验、回答草稿恢复；AI 连接与 Key 复用、模型／推理强度设置。
- 本地流式语音预览与可选 Qwen3-ASR 0.6B 停句校准；权重另行下载，默认不发送音频。高推理与实机语音限制仍明确保留。
- 设置新增官方更新检查、下载及 SHA 校验，不自动安装；修正打包 worker、测试插件和缺少可选依赖时的启动。

### 发布与文档

- 原样发布构建源 `4f93969` 的已验收双平台包；标签包含后续中文文档与归档，不改写包来源。
- 中文下载、系统要求、当前面试流程、连接与语音指南同步；根目录旧报告和已被替代的计划移入历史目录，保留失败及未验收事实。
- [发布说明、校验值及限制](docs/release-notes-v0.4.0-alpha.4.md) · [验收证据](docs/desktop-candidate-20260909-report.zh.md)。

## [0.4.0-alpha.3] - 2026-08-31

### 新增

- 研究型面经/八股/手撕题知识层：63 张带来源 claims、分层答案和角色筛选的卡片，191 条 URL-unique 公开来源登记；新增 VLM/视频、packing、DAPO/GSPO、RAG、Agent 评测、推理 SLO 卡片和 3 个可运行手撕入口，并保留 `llm-lab knowledge list/search/show/validate` 与 `doctor --knowledge` 校验入口；不改变 Practice Grader、Profile 事件或 mastery 语义。

### 修复

- 修复桌面端首次启动、岗位选择、最新答案测试与错误提示的可靠性；
- 练习页在窄窗口下改用真实的题面与 AI 教练入口，移除无法发送的假聊天控件；
- 启动诊断日志补充最小运行环境信息，并同步 Alpha.3 版本元数据。
- 修复岗位首次任务、`ready` 题硬前置与进度证据口径；无 PyTorch 且仅缺代码轮次时，可显式开始不重归一化、始终标为未完整的非代码专项面试。

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

[未发布]: https://github.com/ComistryMo/llm_interview_lab/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0
[0.4.0-alpha.4]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.3...v0.4.0-alpha.4
[0.4.0-alpha.3]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.2...v0.4.0-alpha.3
[0.4.0-alpha.2]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.4.0-alpha.1...v0.4.0-alpha.2
[0.4.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.3.0-alpha.1...v0.4.0-alpha.1
[0.3.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.2...v0.3.0-alpha.1
[0.2.0-alpha.2]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.2.0-alpha.1...v0.2.0-alpha.2
[0.2.0-alpha.1]: https://github.com/ComistryMo/llm_interview_lab/compare/v0.1.0...v0.2.0-alpha.1
[0.1.0]: https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.1.0
