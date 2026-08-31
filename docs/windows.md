# Windows 使用指南

## 系统要求与下载

> 发布状态：当前公开桌面版为 [v0.4.0-alpha.3](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.3)，Windows x64 standalone 包已通过构建、启动和隐私检查。

- Windows 10 / 11 x64；
- Alpha.3 产物为 `LLMInterviewLab-Windows-x64-portable.zip`；
- 对应校验清单为 `SHA256SUMS-Windows.txt`。

Portable ZIP 是完整的 standalone 目录。请先完整解压，再双击
`LLMInterviewLab\LLMInterviewLab.exe`；不要从压缩包预览器中运行，也不要只复制 EXE。
旧 Alpha 的 single-file EXE 启动慢且早期错误不可见，不再作为推荐下载。

## 签名说明

Alpha 可能没有商业代码签名证书。Windows SmartScreen 的来源提示不等于项目已经通过 Microsoft 认证。下载后先校验 SHA-256，只从项目 Release 页面获取文件；哈希不一致时不要运行。

```powershell
Get-FileHash .\LLMInterviewLab-Windows-x64-portable.zip -Algorithm SHA256
```

## 数据目录

Alpha.3 打包应用使用 Qt `QStandardPaths.AppDataLocation` 对应的当前用户 App Data 位置。设置页显示实际路径并可直接打开。真实学习档案不会写入 EXE 或安装目录。

Alpha.1 旧目录 `%LOCALAPPDATA%\LLMInterviewLab` 只在用户确认后迁移。迁移先复制并验证 SHA-256，同时保留旧目录和新目录下的本地备份；不会静默覆盖已有 Profile。

## Credential Manager

普通 LLM API Key 通过系统 Keyring 写入 Windows Credential Manager。Profile 和 `connections.json` 只保存不敏感引用。Credential Manager 不可用时应用不会回退到明文 Key，可继续使用 No-AI。

## Codex

应用检查当前 PATH、npm 常见目录和用户在设置中选择的路径。未安装或未登录不会阻塞本地训练。Codex 使用官方 App Server 与显式审批，不抓取终端 ANSI 文本。

## 常见问题

- **窗口没有显示：** 新版会显示原生中文错误框。请记录错误编号，并查看
  `%LOCALAPPDATA%\LLMInterviewLab\logs\bootstrap.log`；
- **提示运行资源缺失：** 重新完整解压 ZIP；EXE 旁边的 Qt 依赖和
  `runtime_assets` 目录不可删除；
- **首次启动慢：** 安全软件可能首次扫描 standalone 目录；请等待可见窗口，不要连续双击；
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

## 发布前双击验收

发布包必须在 Windows 11 实机或 VM 上只构建一次并逐项确认：

1. 从普通英文路径解压并双击，五秒内出现窗口或明确加载反馈；
2. 从含空格和中文的路径解压并双击；
3. 断网并选择 No-AI，完成岗位选择后进入第一题或首页；
4. 退出重启后，刚创建的学习档案仍然存在；
5. 在发布包副本中临时移走 `runtime_assets`，确认出现含错误编号和日志位置的原生错误框。

验收只使用虚构学习档案；结束后删除故障注入副本，不修改真实用户数据。
