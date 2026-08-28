# 桌面 Alpha 第三方软件声明

桌面构建将 Apache-2.0 许可的 `llm-interview-lab` 与可再分发的第三方软件组合。本页用于帮助理解依赖，不替代各依赖随附的正式许可证；发生差异时以依赖项目许可证原文为准。

## Qt for Python / PySide6

- 项目：Qt for Python（PySide6 / Shiboken6）
- 用途：Qt Quick 桌面界面与平台集成
- 许可：LGPL-3.0-only、GPL 商业双许可等，以实际 wheel 内文件为准
- 来源：<https://doc.qt.io/qtforpython-6/licenses.html>

应用使用动态链接的官方 Python wheel，不修改 Qt。用户应保留 Artifact 中随附的 Qt 许可证文件。

## Python 与打包工具

- CPython：Python Software Foundation License；
- Nuitka：Apache-2.0；
- ordered-set：MIT；
- zstandard：BSD；
- pyside6-deploy：Qt for Python 工具链的一部分。

## 核心 Python 依赖

- PyYAML：MIT；
- jsonschema：MIT；
- pytest：MIT；
- httpx / httpcore：BSD-3-Clause；
- keyring：MIT；
- any-llm 及可选 Provider SDK：以安装或打包的具体版本许可证为准。

## 图标与截图

应用图标由本项目原创，源文件位于 `src/llm_interview_lab/desktop/resources/app-icon.svg`。README 截图来自本项目真实 GUI，不复制第三方项目图片、Logo 或布局素材。

## 构建审计

Release CI 检查构建报告和解包后的 Windows ZIP、macOS APP ZIP 与 DMG，避免包含真实 Profile、API Key、面试记录、Submission、Oracle、Private Tests、`.git` 或本机配置。

依赖版本由 `pyproject.toml` 与部署 Spec 控制。发布前应检查生成物内实际许可证；本页不是完整 SBOM。
