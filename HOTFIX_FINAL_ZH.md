## 基线

- 基线：`main@5e83f8fe3887fd8667bab347931da91fd8bc02a5`（`v0.4.0-alpha.2`）
- 分支：`hotfix/first-run-blockers`
- 初始 dirty state：只有用户提供且未跟踪的 `llm_interview_lab_runtime_blockers_agile_review_zh.md`；未修改、未提交。

## 实际根因

- 岗位选择：`ScrollView → GridLayout → Repeater → Rectangle` 没有给 delegate 可靠的显式几何；同时 `roles[3]` 形成不可见默认选择，导致卡片重叠、选择含义不清。
- 开始训练：`initialize_profile` 在校验 seniority、AI mode 和自评前已经写入 Profile；异常随后被 `friendly_error()` 折叠为 `error.generic`。旧版 Onboarding 失败没有写入 Desktop 日志，因此无法从旧日志恢复用户那次异常；临时数据根复现确认无效 seniority / AI mode 会留下半成品 Profile。
- Windows 无反应：发布配置是 Nuitka one-file，Portable ZIP 仍只包同一个单文件；`prepare_desktop_repository()` 之前没有日志，早期异常只写不可见 stderr，Explorer 双击失败时用户得不到窗口或原因。修正为 standalone 后，Artifact 检查又暴露出 offscreen 截图使用基础 `QWindow`/固定文件大小阈值的问题；最终改为显式包装 `QQuickWindow` 捕获场景，并验证 PNG 解码、尺寸和颜色采样。

临时数据根复现记录（不读取或写入真实 Profile）：

| 输入 | 结果 | 阶段 / 类型 |
|---|---|---|
| `中文 档案` + 合法岗位 + No-AI | 拒绝且不写档案 | `validate` / `WorkspaceError` |
| 合法档案 + 空岗位 | 拒绝且不写档案 | `validate` / 输入错误 |
| 合法档案 + `staff` 阶段 | 拒绝且不写档案 | `initialize_profile` / `ApplicationError` |
| 合法档案 + 非法 AI 模式 | 拒绝且不写档案 | `initialize_profile` / `ApplicationError` |
| 合法档案 + 合法岗位 + No-AI | 进入 `FND-001` | `refresh` / 成功 |

旧版本没有记录 Onboarding 异常正文，因此无法从旧日志还原反馈者当次异常；以上矩阵是对同一路径的可重复复现，而不是对未知旧日志的臆测。

## Luna Max 委派

- Task A：`/root/onboarding_ui`，GPT-5.6 Luna Max；提交 `fa1f7b0`。Main Review 接受显式 `GridView`、主动选择和顶部 Toast，拒绝不可读 tofu 截图，并补齐 `onboardingBusy`、重复提交门控、完整 No-AI 首用 E2E 与三张可读截图。
- Task B：`/root/onboarding_init`；调用失败，HTTP 429，request id `2e5cb7f9-2b5c-4646-b92e-7b3636da71c3`。`LUNA_DELEGATION_UNAVAILABLE`，由 Main 实现并审查。
- Task C：`/root/windows_launch`；调用失败，HTTP 429，request id `41689172-5055-4d66-9acb-3ca378a46385`。`LUNA_DELEGATION_UNAVAILABLE`，由 Main 实现并审查。

## 修改文件

- `OnboardingPage.qml` / `Main.qml`：显式单双列岗位卡、主动选择、选中标记、空状态、内联错误、创建中状态、重复点击门控和顶部 Toast。
- `application.py` / `desktop/controller.py` / `desktop/i18n.py`：输入先校验后写 Profile；Onboarding 专用错误码、脱敏日志、首题失败回首页。
- `desktop/main.py` / `desktop/runtime.py`：Repository 初始化前 bootstrap 日志；运行资源、数据目录、Controller 和 QML 失败的可见 Windows 原生错误框。
- `pysidedeploy.spec` / `ci.yml` / `check_desktop_artifact.py`：Windows 改为 standalone 目录，ZIP 检查运行资源、隐私、版本、GUI 和 bootstrap 日志。
- `README.md` / `docs/windows.md` / `docs/desktop-app.md`：Portable ZIP 成为唯一推荐 Windows 入口，并记录双击验收步骤。
- `tests/infrastructure/test_onboarding_completion_hotfix.py`、`test_onboarding_qml_hotfix.py`、`test_windows_startup_hotfix.py` 及直接相关契约测试：覆盖本次三个阻断点。

## 目标测试

- `python -m pytest tests/infrastructure/test_onboarding_completion_hotfix.py -q`：`15 passed`。
- 三个既有 Application / Controller 定向用例：`3 passed`。
- `python -m pytest ...windows_startup... -q` 首次误用系统 Python 3.9：收集失败（缺少 `jsonschema`），未进入测试；切换 `.venv` Python 3.11.9 后同一目标集：`10 passed, 6 deselected`。
- `test_qml_offscreen_smoke_and_version_do_not_need_a_profile`：`1 passed`。
- Windows 下载文档契约：`1 passed`；bootstrap Windows 路径与脱敏用例：`1 passed`。
- 最终受影响目标集：`10 passed in 5.03s`；Artifact 检查器本地执行：`desktop standalone artifact OK`。
- Luna 原始 UI 目标集：`7 passed`；Main 集成后最终 UI / No-AI 首用目标集：`10 passed`。
- 三张真实 QML 截图：`1536×992`、`1280×800`、`1100×700`；Main 已逐张检查中文、选中态、卡片几何和 CTA。

## 全量与 CI 预算

- 本地全量只运行一次：`386 passed, 12 skipped in 514.68s`。
- 12 个 skip 均为普通 Windows 无 symlink 权限的既有条件；未重复运行本地全量。
- RC 初次 Run：PR #6，`33159456670`；Windows 因固定查找文件名失败。
- 修正文件名后 Run `33161670180`：核心矩阵、文档和 macOS 成功；Windows 在 offscreen 截图阈值处失败。
- Windows 目标测试分流后 Run `33188390663`：测试阶段暴露与本 Hotfix 无关的 Interview 时间敏感用例，未进入打包。
- 修正截图捕获后 Run `33191189866`：PNG 解码成功但颜色阈值过严。
- 最终 Run `33193668556`：仅 Windows Desktop Job，目标测试、standalone 编译、Artifact 检查和上传全部成功。未运行本地全量第二次。

## 实机验收

- 源码 Windows：临时数据根完成 `Post-Training → 跳过自评 → No-AI → 开始训练 → FND-001`，并验证错误路径不写半成品 Profile。
- macOS：本次 macOS 15 arm64 Runner 已完成 QML/offscreen、核心测试、App smoke 和包检查（Job success）；没有伪造外部 Field Run。
- Windows standalone：当前 Windows 机器完成英文路径和含中文/空格路径的双击式启动；No-AI 四步流程成功创建 Profile，重启后 Profile 保留；缺失运行资源时检测到可见标题 `LLM Interview Lab 启动失败`。
- 启动测得首次 bootstrap `first_window_ms` 约 11–12 秒；窗口实际出现但未满足 5 秒目标，需后续优化冷启动或增加可见加载态。

## Artifact

- macOS 候选 Artifact：Run `33161670180`，artifact `LLMInterviewLab-macOS-arm64`，API 报告大小 `364,897,081 bytes`；Job 的 QML/offscreen、App smoke、ZIP/DMG 隐私检查和上传均成功。
- Windows Artifact：Run `33193668556`，外层下载包 `97,870,720 bytes`；其中 `LLMInterviewLab-Windows-x64-portable.zip` 为 `99,062,354 bytes`。
- Windows SHA-256：`7083a1923122f3d62712a708ac34c40be88c118116ac7bb5c5c11dd9c29206e1`。
- Windows 本地解压检查路径：`dist/hotfix-evidence/windows-artifact-73646f/portable/LLMInterviewLab/`（仅为 ignored 验证材料）。
- Bootstrap 日志格式：JSONL，包含 `version`、`startup_stage`、`exception_type`、脱敏 `message`、`runtime_assets_found` 与 `first_window_ms`；默认位置 `%LOCALAPPDATA%\LLMInterviewLab\logs\bootstrap.log`。

示例（临时数据根，未包含答案或密钥）：

```json
{"runtime_assets_found":true,"startup_stage":"process_started","version":"0.4.0a2"}
{"first_window_ms":11371,"runtime_assets_found":true,"startup_stage":"first_window","version":"0.4.0a2"}
```

## 剩余风险

- Windows 首窗冷启动约 11–12 秒，高于 5 秒目标；当前没有加载态提示，这是下一版本可靠性风险。
- macOS 证据来自 macOS 15 arm64 CI Runner，不等同真实外部 Mac 用户 Field Run。
- 未发布 Release，未合并 `main`，未修改或提交真实 Profile。

## 最终裁决

`BLOCKED_BY_COLD_START_TARGET`
