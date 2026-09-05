# 桌面应用指南

桌面版是普通学习者的推荐入口。它使用 PySide6 + Qt Quick，并直接复用与 CLI 相同的 Catalog、Workspace、Planner、Grader、面试引擎与生命周期；普通业务不会调用 CLI 子进程，也不会解析终端输出。

## 安装选择

| 平台 | 文件 | 说明 |
|---|---|---|
| Windows 10 / 11 x64 | `LLMInterviewLab-Windows-x64-portable.zip` | 推荐，完整解压后运行 `LLMInterviewLab/LLMInterviewLab.exe` |
| macOS 12+ Apple Silicon | `LLMInterviewLab-macOS-arm64.dmg` | 推荐，拖入 Applications |
| macOS 12+ Apple Silicon | `LLMInterviewLab-macOS-arm64.app.zip` | 适合直接解压与自动化验证 |
| 开发者 | 源码安装 | 支持调试、完整可选依赖和贡献流程 |

Intel Mac 没有经过真实 Artifact 启动验证，本版不提供 x86_64 或 Universal2 下载承诺。平台细节见 [Windows](windows.md) 与 [macOS](macos.md)。

## 首次启动

两步即可开始：

1. 输入学习档案名称；
2. 从八类岗位中选择目标岗位。

完成后应用会直接进入首页或第一道可用题目，默认使用 No-AI。求职阶段、能力自评和 AI 连接可以稍后在设置、求职材料或模拟面试中补充；自评只影响推荐，不会授予掌握状态。

应用会记住最后一次正常使用的学习档案。下次启动会直接恢复该档案，不会悄悄创建新的档案；如果档案缺失或损坏，页面会给出错误编号和“打开设置切换档案 / 重新创建”的处理入口。设置中的学习档案切换器只读取档案元数据；当前答案未保存或仍有录音、测试、AI 请求时，切换会被阻止并提示下一步。

## 页面

### 首页

只提供两个主要动作：**继续训练** 与 **开始模拟面试**。次级信息包括目标岗位、当前路线、到期复测、最近面试和 AI 状态。

### 求职材料

只添加你拥有、已脱敏且确实需要的文件。文件存在不等于 AI 可以读取；每场面试必须对 material ID、用途和当前 SHA-256 重新授权。文本型 PDF 会提取正文，DOCX 会提取段落和表格，并生成绑定原文件 SHA-256 的只读文本快照；扫描 PDF 暂不做 OCR。无法提取的 PDF / DOCX 仍可仅保存在本机，不能授权给 AI。

### 刷题训练

默认展示岗位推荐路线。答题工作区包括题面、答案编辑器、公开测试、提交、契约审查、口述答辩和 D+2 / D+7；AI 教练从独立页面打开。自动保存不会授权 AI 读取答案。

### 模拟面试

选择岗位、求职阶段、难度与面试官模式。当前动态面试先显示本地的“自我介绍与经历概述”，不等待 AI 生成整场题单。完成回答后，点击“提交并锁定回答”，再点击“让 Codex 继续提问”或普通 API 的“生成下一问”，确认上下文后才发送。AI 返回有效追问时，系统保存本轮证据并展示下一问；界面中的“已展示 N 问”不是整场总题数。

动态面试不要求先填自评分数；固定面试的自评与人工证据入口仍保留。回答锁定后不可改写，新的问题使用空白回答框，已提交的回答仍保存在原题。输入框获焦时提示立即隐藏，中文输入法组字时也不会与提示叠在一起。“语音回答（可选）”可按需展开。

逐轮请求包含目标岗位的技能说明、求职阶段、难度要求、本场已发生的问答、当前回答与本次授权材料。设置页可同时选择简历与一份 JD / 补充经历材料。模型先做经历深挖与针对回答的追问，再进入岗位原理与八股；每个阶段安排 2–4 问，随后从当前可运行、已验证的本地题目中选择一题手撕。只保存已经展示的问题，不预生成未来题单。没有可运行代码题时会保留非代码证据，但不能标记整场完整完成。

手撕题面、接口和测试由本地 Catalog 冻结，代码必须在真实编辑器内作答并运行本地 Grader；模型不能任意编造代码题或宣称测试通过。AI 主观评分引用锁定回答，代码分来自本地测试，两者分别标注来源，不修改 Practice mastery。动态报告按阶段分配权重，不会因为多问几个追问就重复计入整个环节的权重。

Codex 与普通 API 使用同一套逐轮流程及本地结果校验。每次发送都要确认上下文；Codex 使用新的传输 Thread 并显式带上本场历史，避免继承其他场次或本轮取消授权的材料。它仍是连续的一问一答，不依赖 Codex Thread 充当学习记录。当前路径没有传入 `outputSchema`，JSON 提示和本地校验不能称为传输层强制 Schema。模型是否兼容、网络是否稳定仍需按实际服务验证。

动态面试不要求所选难度具备完整固定题单，也不以安装 PyTorch 作为开始条件。“高压”改变追问要求，不会把实习生的本地代码题强行提升到最高难度；代码候选按求职阶段和当前环境筛选。独立刷题入口继续可用。

选择 Codex 后，面试设置中会显示模型与推理强度摘要，并提供“设置模型与推理强度”入口。“已发现”只证明找到程序，“已连接”只证明建立了 App Server 会话，都不保证当前模型兼容。模型要求新版 Codex 时，界面会提示选择新版可执行文件或兼容模型，不再显示泛化错误。请求期间可以点击“停止请求”；中断不会删除已锁定回答。模型请求最长等待 180 秒，超时后关闭该应用拥有的连接并提示重新连接；重试时仍须确认上下文。

如果当前 AI 方式为 **No-AI**，模拟面试页会停留在明确的锁定说明，不会伪造面试 Session、评分或报告。你可以从该页面打开 AI 连接，或返回刷题训练；No-AI 刷题、公开测试、复盘和间隔复测始终可用。

### AI 教练与连接

上下文预览列出将发送的每个部分。普通 Provider 只接收确认文本；Codex 使用官方 App Server，并对写文件和高风险命令展示审批卡片与 Diff。详见 [AI 连接](ai-connections.md)。

设置会在后台检查 Codex 的 PATH、常见安装位置和已保存的可执行文件。状态分为“检查中 / 已发现 / 未发现”，发现时只显示脱敏来源；Finder 或 Explorer 没有继承完整 PATH 时，可用“选择 Codex”指定文件。Codex 不是本地训练或 No-AI 的前置条件。

非代码面试还支持“开始录音 → 停止 → 转录 → 编辑 → 提交”的可选流程。录音默认留在当前学习档案；远程转录前必须单独选择服务并勾选本次授权，转录不会绕过回答锁定步骤。

### 学习进度

自评与验证证据分开显示。岗位准备度只是本地规划指标，不是 Offer 概率或录用判断。

### 设置

可调整主题、字号和界面语言（简体中文默认，English 为实验性选项），切换学习档案，打开数据与日志目录，以及选择或重新自动查找 Codex。Alpha.1 Windows 数据迁移必须由用户确认；应用先复制、计算 SHA-256、保留本地备份，再切换到新位置，绝不删除源目录。

## 当前源码界面（2026-09-05）

本轮借鉴 ChatGPT 的中性色、内容优先与清晰主操作，将面试设置和作答分为两个视图，不再并排展示两块大卡片。保留项目自己的图标、名称和业务流程；设计原则参考 [OpenAI UI 指南](https://developers.openai.com/plugins/concepts/ui-guidelines)，不是对官方客户端的逐像素复刻。

作答时，“本场信息”收纳岗位、难度与状态；提交回答及提交后的 AI 操作固定在底部。长题目和授权材料可以滚动，文字按实际内容高度排布，不通过缩小字体塞进固定行。AI 辅助页使用相同输入样式，获焦和输入法组字时隐藏提示。

以下为正式 QML 页面在 Windows 上的自动交互截图，使用隔离测试档案与合成回答，不是演示 Controller，也不包含真实求职材料。确认弹窗场景使用 **Fake Codex**；其连接标记不证明真实账户可用。截图对应的源码提交、窗口大小和 SHA-256 见 [截图清单](images/chatgpt-ui-20260905/manifest.json)。它们展示当前工作分支，**不是新的桌面 Release**。

| 页面 | 截图 |
|---|---|
| 面试作答 · 1280×800 · 100% 字号 | [浅色](images/chatgpt-ui-20260905/interview-light.png) · [深色](images/chatgpt-ui-20260905/interview-dark.png) |
| 上下文确认 · 1280×800 · 125% 字号 | [深色；Fake Codex 交互验证](images/chatgpt-ui-20260905/context-dark.png) |
| 首页 · 900×620 · 125% 字号 | [浅色；下方内容可滚动](images/chatgpt-ui-20260905/home-small-light.png) |
| AI 辅助 · 900×620 · 125% 字号 | [浅色；中文输入](images/chatgpt-ui-20260905/coach-small-light.png) |

## 快捷键

| 操作 | Windows / Linux | macOS |
|---|---|---|
| 设置 | 系统菜单 | `Command + ,` |
| 运行公开测试 | `Ctrl + R` | `Command + R` |
| 答题页主安全动作（运行测试） | `Ctrl + Enter` | `Command + Enter` |
| 退出 | `Alt + F4` | `Command + Q` |


提交、审批和覆盖类操作不会绑定容易误触的全局快捷键。

## 数据位置

- 源码 / CLI：仓库内 `workspace/`；
- 隔离验收：`LLM_LAB_DESKTOP_DATA_ROOT` 可指定独立目录，源码模式从当前安装的源码位置补齐公共资产，不复制真实学习档案；
- 打包桌面：Qt `QStandardPaths.AppDataLocation`；
- Windows 与 macOS 均不会把真实数据写入 EXE、`.app/Contents/` 或安装目录；
- 设置页会显示并打开实际目录。

日志使用小型滚动文件，默认不上传，不记录 API Key、Authorization Header、完整材料、完整答案、Oracle、Private Tests 或其他学习档案。

## 无 AI 模式

以下故障都不应阻止本地训练：断网、缺少或错误 Key、429 / 500、Ollama 未启动、Codex 未安装或未登录、Keyring 不可用。界面会给出中文下一步，并保留 No-AI 入口。

## 源码运行

```bash
python -m venv .venv
# 激活环境
python -m pip install -e ".[desktop,ai,dev]"
llm-lab-gui
```

离屏 Smoke：

```bash
llm-lab-gui --smoke-test
llm-lab-gui --screenshot desktop-home.png --screenshot-page home
```

## 开发与打包

Windows 使用：

```powershell
python scripts/generate_desktop_icons.py --output dist/icons
pyside6-deploy -c scripts/pysidedeploy.spec -f
```

macOS Apple Silicon 使用：

```bash
python scripts/build_macos_desktop.py
python scripts/check_macos_artifact.py \
  dist/release-macos/LLMInterviewLab-macOS-arm64.app.zip \
  dist/release-macos/LLMInterviewLab-macOS-arm64.dmg
```

GUI 依赖是可选依赖，不会拖入核心 CLI 测试矩阵。CI 使用离屏 QML Smoke、Fake Provider、Fake Codex 和 Mock Keyring，不访问真实账户。

## 排错

- **窗口无法启动：** 先运行 `llm-lab-gui --smoke-test`，再从设置打开日志目录；源码用户运行 `python -m pip install -e ".[desktop,ai,dev]"`。
- **Windows 双击无窗口：** 查看原生错误框中的错误编号和
  `%LOCALAPPDATA%\LLMInterviewLab\logs\bootstrap.log`；确保解压了完整目录，而不是只复制 EXE。
- **Ollama 连接失败：** 确认 Ollama 已启动，地址通常为 `http://127.0.0.1:11434`，然后重新测试。
- **Codex 未检测到：** macOS Finder 不一定继承 Shell PATH；从设置选择 Codex 可执行文件。
- **密钥环不可用：** 应用不会写明文 Key。继续使用 No-AI，并先修复系统 Keychain / Credential Manager。
- **PyTorch 题缺少依赖：** 源码安装执行 `python -m pip install -e ".[torch,dev]"`。

本地 Grader 只用于运行你本人信任的代码，不是恶意代码安全沙箱。

## Phase 2 视觉与验证证据

当前正式页面的合成截图（不含真实档案、答案、材料或密钥）位于 [`docs/images/phase2/`](../docs/images/phase2/)，由该目录中的 `manifest.json` 记录页面、尺寸、主题和 SHA-256。它们用于核对首用入口、首页、首题、面试页面和设置布局；截图不会替代真实 Profile 或跨平台实机验收。
