# 真实用户迭代最终报告

## 基线

- HEAD：`e1536f2b61c39d833a86a9ff3d19464fa50a2c73`
- 分支：`feature/real-user-iteration-20260831`
- 基线来源：`v0.4.0-alpha.3` / `36db5ac3ba21580323a5116e356830badabcc0f4`
- 工作树：已提交的改动之外干净；用户已有的未跟踪文件未读取、未修改。
- Python：`3.11.9`（`py -3.11`）；系统 `python` 为 3.9.2，因此未用它运行项目测试。

## 实际根因

- 岗位选择：现有首用流程本身可以创建岗位，但桌面启动没有可靠记住上次显式选择的 Profile；同时 Linux/offscreen 的字体回退会让中文截图出现不可读字符。现在用按数据根目录隔离的 QSettings 只保存安全的内部 Profile ID，并为 Qt/Python 选择已安装的 CJK 字体。
- 开始训练：创建 Profile 后首题打开与 onboarding 成功被耦合，首题资源异常时容易把用户留在首用页。现在保留 Profile 成功状态，首题失败回退首页并给出可操作提示；默认 Profile 重启时恢复上次有效 Profile。
- 材料权限：PDF/DOCX 只能作为不透明原文件保存，旧界面仍可勾选 AI 读取。现在选择这类文件时提前禁用并解释 AI 权限，后端仍是最终校验者。
- Coach/Home：Coach 新建会话按钮使用旧原生控件导致浅色主题对比不足；输入框原生 placeholder 与自定义提示重叠；紧凑首页的最近面试卡片文字被裁切。已分别改为主题按钮、自定义占位提示和可换行的卡片布局。
- No-AI 面试：无 AI 模式此前仍暴露容易误解的启动入口。现在明确显示 No-AI 边界并提供前往 AI 连接的路径；未配置 AI 不会破坏本地训练。
- Windows 无响应：本轮在当前环境没有可复现的 Windows Explorer 双击打包运行证据，也没有把旧的发布包重新宣称为已验证修复。现有源码级启动/打包契约通过，但真实 Windows 包验收仍是发布阻断项。

## Luna Max 委派

- Task：请求 Luna Max 对 UI、Profile 和 Windows 启动分别进行独立实现/审查。
- 调用标识：多次调用均被服务端限流（HTTP 429）；另一次替代模型因容量不足失败。
- 返回结果：没有可采纳的子 Agent patch 或报告。
- Main Review：按同一任务边界由主控完成最小实现和逐文件审查；未伪造 Luna 输出，状态记为 `LUNA_DELEGATION_UNAVAILABLE`。

## 修改文件

- `.gitignore`：忽略维护者本地截图和探针目录，不改变用户 Profile 规则。
- `plans/active/real-user-iteration-20260831.md`：记录切片、测试预算和未满足的发布条件。
- `src/llm_interview_lab/desktop/controller.py`：恢复/持久化当前 Profile ID，限定显式 Profile 优先，不枚举其他 Profile。
- `src/llm_interview_lab/desktop/i18n.py`：为 PDF/DOCX 能力边界提供可执行中文提示。
- `src/llm_interview_lab/desktop/main.py`：为 Linux 原生 Qt 控件选择可用 CJK 字体。
- `src/llm_interview_lab/desktop/qml/Main.qml`：统一字体回退，并向 Coach 页传递主题对象。
- `src/llm_interview_lab/desktop/qml/pages/CareerPage.qml`：在导入前展示 PDF/DOCX 的 AI 能力限制并防止错误授权。
- `src/llm_interview_lab/desktop/qml/pages/CoachPage.qml`：统一主按钮主题、修复模型标签和输入框占位提示布局。
- `src/llm_interview_lab/desktop/qml/pages/HomePage.qml`：修复紧凑宽度下最近面试卡片裁切。
- `src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml`：明确 No-AI 面试边界和 AI 连接入口。
- `tests/infrastructure/test_desktop.py`：补充 Profile 恢复、材料能力和页面契约覆盖。
- `tests/infrastructure/test_onboarding_completion_hotfix.py`：补充默认 Profile 重启恢复和 No-AI 首用路径。
- `docs/images/*`、`docs/images/screenshot-manifest.json`：使用当前代码生成 64 格合成截图矩阵，标记 `synthetic: true`。
- `REAL_USER_ITERATION_FINAL_ZH.md`：本报告。

## 目标测试

使用 Python 3.11 定向执行，未用系统 Python 3.9：

- `py -3.11 -m pytest tests/infrastructure/test_onboarding_completion_hotfix.py -k "default_desktop_restart_restores_the_last_profile or clean_no_ai_onboarding" -q`：`2 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_onboarding_qml_hotfix.py -q`：`12 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_career_materials.py -q`：`20 passed, 3 skipped`。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "interview_setup_uses_profile_role_availability_and_real_report or no_ai_interview_setup_explains_the_ai_boundary or material_import_disables_ai_consent" -q`：`3 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "truthful_desktop_pages_render_at_1080x680" -q`：`4 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_desktop.py -k "truthful_desktop_pages_render_at_1080x680 or coach" -q`：`4 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_desktop_platform.py -q`：`4 passed, 1 skipped`。
- `py -3.11 -m pytest tests/infrastructure/test_coach_sessions.py -q`：`5 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_chinese_docs.py -q`：`10 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_windows_startup_hotfix.py -q`：`9 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_alpha4_home_p1.py -q`：`4 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_alpha4_learn_p1.py -q`：`4 passed`。
- `py -3.11 -m pytest tests/infrastructure/test_alpha3_truthful_ux.py -q`：`12 passed, 1 skipped`。
- `py -3.11 -m pytest tests/infrastructure/test_alpha4_screenshot_contract.py -q`：`2 passed`。
- `git diff --check`、目标 Python `py_compile`：通过。
- 本轮唯一一次本地全量：`py -3.11 -m pytest -q` → **`507 passed, 14 skipped in 834.32s`**。

截图证据：`py -3.11 scripts/capture_desktop_screenshots.py --theme all --delay-ms 250` 成功生成 64 格矩阵；人工查看 Windows QPA 的 onboarding、home、coach 截图，未见岗位卡片重叠、选中态消失或输入框文字碰撞。

## 全量与 CI 预算

- 本地全量只运行了一次，结果见上。
- 本轮没有触发新的 RC CI，也没有重复整个 CI 矩阵；因此不能声称远端 CI 已验证本 patch。
- 曾有一次错误的测试文件名命令返回“file not found”，没有进入测试收集；随后使用正确命令完成截图契约验证。

## 实机验收

- macOS：未在本轮使用真实 Mac 设备或新打包产物验收；不能宣称 macOS 首用通过。
- Windows：未取得本轮 standalone 包的 Explorer 双击、中文路径、空格路径、断网和损坏资源实机证据；不能宣称 Windows 双击问题已修复。
- 当前可确认的是源码/测试环境中的 No-AI 页面、Profile 恢复、QML 页面和启动契约行为。

## Artifact

- 本轮没有生成或发布新的 Windows/macOS 安装包。
- `docs/images/` 中的截图均为合成数据，Manifest 标记 `synthetic: true`；不含真实 Profile、答案、材料、Key、Oracle 或 Private Tests。
- 因没有真实候选 Artifact，本报告不提供虚构的文件大小或 SHA-256。

## 剩余风险

- `LUNA_DELEGATION_UNAVAILABLE`：本轮没有外部子 Agent 结果可交叉审查。
- `BLOCKED_BY_MISSING_WINDOWS_RUNTIME`：缺少本轮 Windows standalone Explorer 双击验收。
- `BLOCKED_BY_MISSING_MACOS_RUNTIME`：缺少本轮 macOS 打包/真实设备验收。
- 语音转写 MVP 仍未实现；本轮未扩大范围。
- 全量测试虽通过，但 QML 后端为空的既有 fixture 会打印 TypeError 警告；未改变其既有测试语义。

## 最终裁决

**PARTIAL — P0 源码与定向验证完成；发布/实机门禁未满足。**

可以继续审查或推送当前功能分支，但在 RC CI、Windows standalone 双击和 macOS 产物验收完成前，不应合并 `main`、打新 tag 或发布 Release。
