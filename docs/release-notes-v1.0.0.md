# v1.0.0 · 首次正式发布

LLM Interview Lab 是面向 AI 求职者的中文桌面练习工具。本次统一以 **v1.0.0** 对外发布，此前的 0.x / Alpha 编号属于开发期，不再作为当前产品版本。

[下载本版](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0) · [使用指南](https://github.com/ComistryMo/llm_interview_lab/blob/v1.0.0/docs/desktop-app.md)

## 这一版可以做什么

- **AI 模拟面试**：带上脱敏简历与 JD，从自我介绍、经历深挖、岗位原理到手撕，一次生成下一问，提交回答后继续。
- **按岗位和难度练习**：八类 AI 岗位，简单／标准／困难三种难度；不按实习、校招、年限分档。难度改变提问深广度，不改变评分宽容程度。
- **手撕与知识练习**：中文题面、英文切换、代码编辑、自写样例运行、公开测试与相关知识卡。
- **面试复盘**：保留问答和代码，依据实际回答评价优势、缺口与下一步练习。缺少证据的部分不虚构评分。
- **自己的 AI 连接**：DeepSeek、OpenAI-compatible、Ollama、Codex；模型与支持的推理强度可选，Key 保存在系统密钥环。
- **本地语音**：边说边预览文字，停句自动校准；首次在「语音设置」点击「下载本地模型」，约 1.19 GB，自动校验安装，不需语音 API Key。
- **日常使用**：恢复上次档案与配置、可收起侧栏、深浅主题、中文输入、材料本地提取与逐场发送范围确认。

## 下载与安装

| 系统 | 文件 |
|---|---|
| Windows 10 / 11 x64 | [完整便携 ZIP](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-Windows-x64-portable.zip) |
| macOS 14+ Apple Silicon | [DMG](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.dmg) / [APP ZIP](https://github.com/ComistryMo/llm_interview_lab/releases/download/v1.0.0/LLMInterviewLab-macOS-arm64.app.zip) |

Windows 完整解压后启动 LLMInterviewLab.exe，不能单独移动 exe。macOS 打开 DMG，将应用拖入「应用程序」。不提供 Intel / Universal2 包。

三个包的 SHA-256 见 Release 附件 SHA256SUMS.txt，同时提供 Windows 与 macOS 独立清单。下载和应用内版本均应为 1.0.0；旧开发包不通过改名当作 v1 包。

## 使用前请了解

- Windows 没有商业代码签名；macOS 使用 ad-hoc 签名，未使用 Apple Developer ID、未经过 Apple 公证。请核对下载来源和 SHA，不要关闭系统安全保护。
- 不连接 AI 也能本地刷题；个性化模拟面试需要自己的模型服务。云端 API 费用由服务商收取，本项目不提供云端额度。
- 材料、录音和学习记录保存在本机。确认发送范围后，远程面试官才接收相应背景与提交的回答；本地语音失败不会自动上传。
- 包内未安装 PyTorch；需要相关手撕题时使用源码环境。公共内容有 96 个已备齐资产的节点，其中 84 个经过 Oracle 验证、12 个仅契约级；158 个待建设节点不是可练题。24 道具备复测变式、255 张知识卡、258 条来源。可运行资格还取决于环境与前置练习。
- DeepSeek 高推理仍有空正文或请求失败的已知记录；失败后可保留回答重试。模型可用性和时延取决于服务商与网络。
- 语音模型首次联网下载，之后本机识别。首次加载可能较慢，专业术语、口音和噪声仍会影响准确率，提交前请检查文字。
- 本地执行只适用于你信任的代码，不是恶意代码沙箱。AI 代码评价不能替代真实运行结果，面试分数不代表求职录用概率。

## 验证范围与历史

本次只调整对外版本、README 与发布材料，不改面试、题目、评分或语音逻辑。Windows/macOS 包已从 1.0.0 源码重新构建；Windows 的 83 项桌面检查、macOS 的 960 项检查（8 项跳过），以及启动、ZIP／DMG 产物检查均通过。构建源为 `8fe697c`，完整记录见[本次 CI](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34305123396)与[发布验证说明](https://github.com/ComistryMo/llm_interview_lab/blob/v1.0.0/docs/release-process.zh.md)。

此前的自动化、合成数据与原生验收记录保留在[开发期报告](https://github.com/ComistryMo/llm_interview_lab/blob/v1.0.0/docs/desktop-candidate-20260909-report.zh.md)，不冒充本次新增人工验收。未完成的 macOS 用户实机、全新 Windows 虚拟机及真实模型／麦克风验收仍是限制。

Field-tested runs：0。自动化与合成数据不计作真实学习者验证。

## 更新与数据

退出旧应用再替换程序，保留应用数据目录、模型和自己的备份。设置页可查看实际数据目录。此次版本命名调整不清空档案、答案、材料、Key 或录音。

旧开发版不再作为推荐下载入口。本次发布流程先确认 v1 下载就绪，再备份和移除此前七个 GitHub 开发版 Release 的页面与附件；备份保留 90 天，Git 提交与历史标签保留。新用户只需要使用本页的 v1 下载。
