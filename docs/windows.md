# Windows 使用指南

## 系统要求与下载

> 发布状态：当前公开桌面版为 [v0.4.0-alpha.4](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.4)，Windows x64 standalone 包已通过构建、启动和隐私检查。

- Windows 10 / 11 x64；
- Alpha.4 产物为 `LLMInterviewLab-Windows-x64-portable.zip`；
- [下载 Windows ZIP](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/LLMInterviewLab-Windows-x64-portable.zip)；
- [SHA256SUMS-Windows.txt](https://github.com/ComistryMo/llm_interview_lab/releases/download/v0.4.0-alpha.4/SHA256SUMS-Windows.txt)。

Portable ZIP 是完整的 standalone 目录。请先完整解压，再双击
`LLMInterviewLab\LLMInterviewLab.exe`；不要从压缩包预览器中运行，也不要只复制 EXE。
旧 Alpha 的 single-file EXE 启动慢且早期错误不可见，不再作为推荐下载。

## 签名说明

本版没有商业代码签名证书。Windows SmartScreen 的来源提示不等于项目已经通过 Microsoft 认证。下载后先校验 SHA-256，只从项目 Release 页面获取文件；哈希不一致时不要运行。

```powershell
Get-FileHash .\LLMInterviewLab-Windows-x64-portable.zip -Algorithm SHA256
```

## 数据目录

Alpha.4 打包应用使用 Qt `QStandardPaths.AppDataLocation` 对应的当前用户 App Data 位置。设置页显示实际路径并可直接打开。真实学习档案不会写入 EXE 或安装目录。

Alpha.1 旧目录 `%LOCALAPPDATA%\LLMInterviewLab` 只在用户确认后迁移。迁移先复制并验证 SHA-256，同时保留旧目录和新目录下的本地备份；不会静默覆盖已有 Profile。

## Credential Manager

普通 LLM API Key 通过系统 Keyring 写入 Windows Credential Manager。Profile 和 `connections.json` 只保存不敏感引用。Credential Manager 不可用时应用不会回退到明文 Key，可继续使用 No-AI。

## Codex

应用检查当前 PATH、npm 常见目录和用户在设置中选择的路径。未安装或未登录不会阻塞本地训练。Codex 使用官方 App Server 作为面试官，不抓取终端 ANSI 文本。已保存连接在启动后恢复，普通 API 不依赖 Codex。

## 常见问题

- **窗口没有显示：** 新版会显示原生中文错误框。请记录错误编号，并查看
  错误框给出的日志位置；能进入应用时使用“设置 → 打开日志目录”，不要假定与旧版路径相同；
- **提示运行资源缺失：** 重新完整解压 ZIP；EXE 旁边的 Qt 依赖和
  `runtime_assets` 目录不可删除；
- **首次启动慢：** 安全软件可能首次扫描 standalone 目录；请等待可见窗口，不要连续双击；
- **PyTorch 题不可用：** 本版不内置 PyTorch，27 道已验证代码题具备包内环境；需要其他题时源码安装 `.[torch,dev]`；
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

## 本版验收与升级

Windows 原生已完成合成档案的建档、中文题面、脚本/公开测试、保存、重启与数据保留；最终 CI 下载包也在当前 Windows 上启动恢复。实际主机有开发工具，不冒称全新 VM、麦克风或真实 AI 已验收。详见[构建与 UAT 报告](desktop-candidate-20260909-report.zh.md)。

升级：先退出旧版，解压到新目录启动，不要删除设置中显示的数据目录。保留旧包与数据备份便于回退。维护者后续原生验收关注：

1. 从普通英文路径解压并双击，出现窗口或明确加载反馈；
2. 从含空格和中文的路径解压并双击；
3. 断网并选择 No-AI，完成岗位选择后进入第一题或首页；
4. 退出重启后，刚创建的学习档案仍然存在；
5. 在发布包副本中临时移走 `runtime_assets`，确认出现含错误编号和日志位置的原生错误框。

验收只使用虚构学习档案；不在真实用户安装目录故障注入。性能受磁盘、安全软件与首次加载影响，不承诺固定启动秒数。

本地语音需首次下载权重，详见[本地语音指南](local-stt.md)。[返回中文文档](README.md)。
