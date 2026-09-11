# macOS 使用指南

> 发布状态：当前公开桌面版为 [v1.0.0](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0)，提供 Apple Silicon 的 DMG 与 APP ZIP，下载与验证状态见[v1 发布说明](release-notes-v1.0.0.md)。

构建目标为 macOS 15 Apple Silicon CI，包含启动、代码/测试 worker、ZIP 与 DMG 挂载检查。尚未做 macOS 用户实机或麦克风验收；[开发期证据](desktop-candidate-20260909-report.zh.md)保留原测试日期，不因 v1 更名算作重新验收。

## 系统要求

- Apple Silicon（M1、M2、M3、M4 或更新）；
- **macOS 14 或更新**（完整 Qt / NumPy / SciPy 运行时要求）；
- 使用 DMG / APP ZIP 安装包不要求自行安装 Python；从源码运行需单独准备 Python，见[源码启动步骤](desktop-app.md#源码运行)；
- AI 连接可选，无网络也能使用本地课程；个性化模拟面试需要 AI，No-AI 下显示连接说明，不创建假面试。

构建参数和 `LSMinimumSystemVersion=14.0` 与 CI 实际安装的最高 wheel 平台要求一致。[Qt 6.11](https://doc.qt.io/qt-6/supported-platforms.html#macos) 自身要求 13，[NumPy 的 Accelerate wheel](https://numpy.org/doc/2.0/release/2.0.0-notes.html#macos-accelerate-support-including-the-ilp64) 则区分 14+。旧 Alpha.3 元数据不回写；项目不宣称已实测全部 macOS 版本。

## 下载哪个文件

| 文件 | 适合场景 |
|---|---|
| [LLMInterviewLab-macOS-arm64.dmg](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.dmg) | 普通用户安装 |
| [LLMInterviewLab-macOS-arm64.app.zip](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.app.zip) | 直接解压、自动化验证或 DMG 有问题时 |
| [SHA256SUMS.txt](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/SHA256SUMS.txt) | 校验下载完整性 |

v1.0.0 不提供 Intel x86_64 或 Universal2 Artifact。没有通过真实架构与启动验证的包不会仅靠重命名发布。

## DMG 安装

安装步骤：

1. 下载 DMG 与 `SHA256SUMS.txt`；
2. 校验 SHA-256；
3. 打开 DMG；
4. 把 `LLMInterviewLab.app` 拖到 Applications；
5. 首次启动如遇 Gatekeeper 提示，确认校验值正确后，在系统设置 → 隐私与安全中选择打开。

## APP ZIP

双击解压，得到 `LLMInterviewLab.app`。可移动到 Applications，也可从用户目录启动。不要直接修改 `.app/Contents/`。

## SHA-256 校验

```bash
shasum -a 256 LLMInterviewLab-macOS-arm64.dmg
shasum -a 256 LLMInterviewLab-macOS-arm64.app.zip
cat SHA256SUMS.txt
```

哈希不一致时不要运行文件，请重新下载并报告 Release 问题。

## 签名与公证

v1.0.0 发布构建使用 ad-hoc signing：

- 未使用 Apple Developer ID；
- 未经过 Apple Notarization；
- 不代表 Apple 已验证，也不代表“无安全风险”；
- CI 仍执行 `codesign --verify`，但这是 Bundle 完整性检查，不是开发者身份认证。

如果未来 Release 使用真实 Developer ID 和 Notarization，Release Notes 会明确写出并附 `spctl` / staple 验证结果。凭证只来自 GitHub Secrets。

## 数据存储

打包应用通过 Qt `QStandardPaths.AppDataLocation` 保存数据，通常在：

```text
~/Library/Application Support/LLM Interview Lab/
```

学习档案、答案、材料、面试 Transcript、Cache 和连接元数据不会写入 `/Applications/LLMInterviewLab.app/Contents/`。设置页可查看和打开实际目录。

源码模式仍使用仓库内 `workspace/`，两种模式共用 Workspace 业务逻辑。

## Keychain

普通 LLM API Key 写入 macOS Keychain。配置文件只保存不敏感的 `key_reference`。应用重启后从 Keychain 读取；删除连接时删除对应 Key。

Keychain 不可用时不会把 Key 写入明文文件。应用会给出中文提示，并允许继续 No-AI。

## Codex 查找

Finder 启动的 App 可能没有完整 Shell PATH。应用检查当前 PATH、Homebrew 常见位置与用户安装目录，也允许在设置中选择 Codex 可执行文件。

检测不到时：

1. 确认 Codex 已安装并能在 Terminal 启动；
2. 在设置中点击“选择 Codex”；
3. 重新打开 AI 连接并测试；
4. 未解决前继续 No-AI 或普通 LLM API。

Codex 使用官方 App Server，不解析交互式终端输出。

## macOS 快捷键与体验

- `Command + ,`：设置；
- `Command + R`：答题页运行公开测试；
- `Command + Enter`：答题页执行主安全动作（运行测试）；
- `Command + Q`：退出。

应用提供原生菜单、High DPI、深浅主题和中文输入；跨平台自动化覆盖了窗口布局和中文路径，不代表每种 macOS 实机和输入法都已验收。

## 常见问题

- **“无法验证开发者”：** 本版未公证。先核对 SHA-256，再从隐私与安全页面确认；不要用来路不明的绕过命令。
- **App 无法打开：** 确认是 Apple Silicon；本版需要 macOS 14+。查看对应版本的已知限制。
- **Codex 未检测到：** 在设置选择可执行文件。
- **Ollama 连接失败：** 先启动 Ollama，再测试本地地址。
- **Keychain 拒绝访问：** 不会保存明文 Key；先用 No-AI。
- **日志位置：** 设置 → 打开日志目录；日志默认不上报。

## 源码运行与开发

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[desktop,ai,dev]"
llm-lab-gui
```

构建 arm64 Artifact：

```bash
python scripts/build_macos_desktop.py
```

该脚本生成原创 `.icns`、调用 `pyside6-deploy`、配置 Info.plist、ad-hoc sign、运行内部 `--version / --smoke-test`、创建 APP ZIP / DMG 与 SHA-256。构建必须在 arm64 macOS 主机执行。

## 更新与可选依赖

先退出旧应用，再替换 Applications 中的应用；不要删除数据目录。设置可打开实际路径，保留数据备份和旧包便于回退。语音模型权重单独下载，不随包提供；PyTorch 未内置，需要相应题目时使用源码环境。缺依赖不等于题面缺失。

[本地语音指南](local-stt.md) · [返回中文文档](README.md)
