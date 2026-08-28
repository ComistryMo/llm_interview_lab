# Windows 使用指南

## 系统要求与下载

- Windows 10 / 11 x64；
- 普通用户推荐 `LLMInterviewLab-Windows-x64-portable.zip`；
- 单文件下载为 `LLMInterviewLab-Windows-x64.exe`；
- `SHA256SUMS.txt` 或 Windows 校验清单用于验证完整性。

Portable ZIP 解压后运行 `LLMInterviewLab-Windows-x64.exe`。不要直接在压缩包预览器中运行。

## 签名说明

Alpha 可能没有商业代码签名证书。Windows SmartScreen 的来源提示不等于项目已经通过 Microsoft 认证。下载后先校验 SHA-256，只从项目 Release 页面获取文件；哈希不一致时不要运行。

```powershell
Get-FileHash .\LLMInterviewLab-Windows-x64.exe -Algorithm SHA256
Get-FileHash .\LLMInterviewLab-Windows-x64-portable.zip -Algorithm SHA256
```

## 数据目录

Alpha.2 打包应用使用 Qt `QStandardPaths.AppDataLocation` 对应的当前用户 App Data 位置。设置页显示实际路径并可直接打开。真实学习档案不会写入 EXE 或安装目录。

Alpha.1 旧目录 `%LOCALAPPDATA%\LLMInterviewLab` 只在用户确认后迁移。迁移先复制并验证 SHA-256，同时保留旧目录和新目录下的本地备份；不会静默覆盖已有 Profile。

## Credential Manager

普通 LLM API Key 通过系统 Keyring 写入 Windows Credential Manager。Profile 和 `connections.json` 只保存不敏感引用。Credential Manager 不可用时应用不会回退到明文 Key，可继续使用 No-AI。

## Codex

应用检查当前 PATH、npm 常见目录和用户在设置中选择的路径。未安装或未登录不会阻塞本地训练。Codex 使用官方 App Server 与显式审批，不抓取终端 ANSI 文本。

## 常见问题

- **窗口没有显示：** 从 PowerShell 运行 `LLMInterviewLab-Windows-x64.exe --smoke-test`，再查看设置中的日志目录；
- **首次启动慢：** 单文件构建需要解包；Portable ZIP 中的单文件仍可能受杀毒扫描影响；
- **PyTorch 题不可用：** 便携包不承诺捆绑完整 CPU PyTorch，源码安装 `.[torch,dev]`；
- **Ollama 失败：** 启动 Ollama 并检查 `http://127.0.0.1:11434`；
- **SmartScreen：** 先核对 Release 与 SHA-256，不要关闭全局安全防护；
- **路径含空格或中文：** 已纳入跨平台测试；如仍失败请提交最小复现，不上传真实 Profile。

## 源码运行

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[desktop,ai,dev]"
llm-lab-gui
```

本地 Grader 会执行用户本人信任的代码，不是恶意代码安全沙箱。
