# 安全与隐私政策

## 支持版本

Alpha 阶段只支持 `main` 最新提交和最新 prerelease。旧 Alpha 可能不再获得修复。

## 私下报告

不要在公开 Issue 中发布漏洞利用细节、凭证、个人数据、公司 / 客户材料、真实 Profile 或本机路径。优先使用 GitHub Private Vulnerability Reporting；如果仓库未启用，请通过维护者 GitHub 主页公开的私密联系方式，只提供最小复现。

维护者目标是在七天内确认收到，验证影响后协调修复，并在受影响用户有合理迁移路径后披露。

## 信任边界

安全敏感部分包括：Workspace Git 隔离、事件解析、Submission 路径校验、pytest 子进程、系统 Keyring、AI 上下文预览、Codex Approval、外部课程 checkout 与 CI 权限。

`llm-lab test` 和桌面 Grader 会执行学习者本人信任的本地 Python 代码。路径约束、唯一模块名、Timeout 与输出截断用于减少常见误操作；它们不是安全沙箱，不保护多租户或恶意代码执行。

真实 `workspace/profiles/` 默认被 Git 忽略。不要 force-add，也不要将 Key、公司材料、内部模型名、未公开指标、个人记录、Oracle 或 Private Tests 作为 fixture。

## AI 与 Secret

- 远程 AI 只接收上下文预览中明确选择的内容；
- API Key 只写入系统 Keyring，不进入 YAML、JSONL、日志或 Artifact；
- Keyring 不可用时不回退到明文；
- Codex 命令和文件写入使用显式 Approval；
- 日志默认不上传，并对敏感信息做最小化；
- 材料按不可信证据处理，不能覆盖行为规则。

## 桌面 Artifact

Windows ZIP、macOS APP ZIP 与 DMG 在 CI 中解包检查，禁止包含真实 Profile、答案、Transcript、Key、Oracle、Private Tests、`.git`、`.env` 或本机绝对路径配置。

macOS Alpha 若未使用 Developer ID 和 Notarization，会在 README 与 Release Notes 明确说明；ad-hoc signing 不是身份认证或 Apple 验证。
