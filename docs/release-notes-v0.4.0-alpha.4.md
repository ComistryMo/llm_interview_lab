# v0.4.0-alpha.4 · 中文桌面版

发布日期：2026-09-09。此版本公开发布 Windows x64 与 macOS Apple Silicon 应用，仍标为 **Alpha 预发布**，不是 Beta 或稳定版。

[下载 Release](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v0.4.0-alpha.4) · [Windows 安装](https://github.com/ComistryMo/llm_interview_lab/blob/v0.4.0-alpha.4/docs/windows.md) · [macOS 安装](https://github.com/ComistryMo/llm_interview_lab/blob/v0.4.0-alpha.4/docs/macos.md) · [完整中文文档](https://github.com/ComistryMo/llm_interview_lab/blob/v0.4.0-alpha.4/docs/README.md)

## 相对 Alpha.3 的主要变化

- 中文优先、统一的 Graphite Blue 深浅主题、完整输入控件和更克制的页面层级；侧栏可收起，移除左下重复档案装饰，档案切换保留在设置。
- 首页围绕开始／继续面试、当前练习、记录和复盘组织；准备页恢复上次配置。宽屏面试与代码区更充分使用空间，小窗口保留可达操作与滚动。
- 新模拟面试不再按实习／校招／年限分档。岗位决定方向，获准经历决定切入点，简单／标准／困难决定深度和广度。
- 只生成下一问，不在开始时冻结整场题单。提交一次保存并继续，AI 等待不扣作答时间；结束再后台评分，成功评分不重复请求，缺少证据不制造高分。
- 经历深挖、岗位原理和手撕按覆盖与时间推进。手撕只接受真实可运行候选 ID；共享原生编辑器，自己运行样例、公开测试与 AI 代码评价分开。
- 固定代码题默认展示完整中文要求，保留原题切换，不改接口、公开测试或掌握条件。补齐算法、Attention、后训练及研究知识内容与真实练习关联。
- 口述回答和知识练习防抖保存，重启恢复不提交、不评分；代码保留保存及关闭确认，不承诺断电恢复尚未保存的代码。
- PDF/DOCX 本地文本提取与 SHA 快照、同档案配置恢复、有效材料组合偏好恢复；新场次仍确认发送范围，材料变化或撤权不沿用旧许可。
- API Key 在系统密钥环保存、复用、修改与删除；DeepSeek 快捷配置，Codex 模型与推理强度设置、会话复用。启动恢复连接，探测不发送材料；普通 API 探测可能产生少量服务商计费。
- 本地流式语音预览 + Qwen3-ASR 0.6B 停句校准；模型单独下载到本机，不包含在安装包内，不需要语音 API Key。
- 知识搜索复用已验证公共快照，提高检索速度；文件变化重新验证，不缓存个人授权。
- 设置提供官方 Release 检查、预发布渠道、下载、取消及 SHA 校验；不会自动安装或覆盖当前程序。
- 修正便携执行 worker、公开测试插件与缺少可选依赖时的首用行为；系统 PATH 没有 Python 也可执行包内支持的代码和公开测试。

## 下载与校验

| 文件 | 大小（字节） | SHA-256 |
|---|---:|---|
| LLMInterviewLab-Windows-x64-portable.zip | 172108416 | a162c20dfe281c6f24f2915b9df4439ca7fcfd3ebc1245a72ddc0f29abed0178 |
| LLMInterviewLab-macOS-arm64.app.zip | 231667572 | 1d01879fb1e72973d9cfd45a96b22fcc11becd0b6f60532b2ec25e2d62845090 |
| LLMInterviewLab-macOS-arm64.dmg | 272313332 | e03bfc10fa280f84cc680548bda113b139ce14a817650503d5ede9bc18e694e2 |

Release 同时提供 SHA256SUMS.txt、SHA256SUMS-Windows.txt 和 SHA256SUMS-macOS.txt。SHA 只证明与发布清单一致，不是代码签名或安全审计。

Windows 10/11 x64：完整解压后启动 LLMInterviewLab.exe，不能只复制 exe。
macOS：Apple Silicon、**macOS 14+**；完整 Qt/NumPy/SciPy 运行时需要 14，不沿用 Alpha.3 的 12+。
macOS 为 ad-hoc 签名，**没有 Apple Developer ID 或公证**。不提供 Intel / Universal2 包。Windows 也没有商业代码签名。

## 构建来源与门禁

三个包原样来自 [CI 34288557804](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34288557804)，构建源为 **4f939695ce0d411356f6121ea46e5569018366a2**。
发布标签额外包含中文说明、文档归档和发布校验；应用、课程与构建输入保持不变。包内 BUILD-METADATA 保留实际构建源，不改写 SHA 冒充重建。

此前完整构建门禁：

| 检查 | 结果 |
|---|---|
| Ubuntu Python 3.10 / 3.11 / 3.12 | 各 650 passed、32 skipped |
| Windows 核心 Python 3.10 / 3.11 / 3.12 | 各 649 passed、33 skipped |
| CPU PyTorch 专项 | 2 passed |
| 中文文档契约 | 28 passed |
| Windows 桌面专项 | 83 passed，构建、worker 与包隐私检查通过 |
| macOS 15 arm64 | 944 passed、8 skipped，构建、启动、worker、签名完整性、ZIP/DMG 挂载检查通过 |

Windows 实际原生包已完成隔离建档、中文题面、代码保存、自写脚本、公开测试、提交、重启及旧合成数据升级。
最终 CI MSVC 包也在当前 Windows 上解包启动，恢复合成档案、练习和代码，退出后私人哨兵文件 SHA 不变。
此前失败和修复、截图及实际命令保留在[候选验收报告](https://github.com/ComistryMo/llm_interview_lab/blob/v0.4.0-alpha.4/docs/desktop-candidate-20260909-report.zh.md)。发布整理只做文档与产物来源检查，没有再次打包或重复全量回归。

## 内容口径

96 道 ready 题：84 道 Oracle 验证、12 道契约级；158 个 planned 节点不是可练题。
24 道有已验证 D+2/D+7 变式，255 张知识卡、258 条去重来源。待审 AUTHOR 资产不计入已验证数量。

包内未安装可选 PyTorch，**27 道已验证代码题具备运行环境**，不能宣传成全部 96 道均可执行。
全部公共资产随包的清单与源码 SHA 已核对；详见[覆盖快照](https://github.com/ComistryMo/llm_interview_lab/blob/v0.4.0-alpha.4/docs/content/release-candidate-coverage-20260909.zh.md)。

## 更新与回退

先退出旧应用，Windows 解压到新目录，macOS 再替换应用；**不要删除应用数据目录**。
启动仅更新公共课程与规则，不覆盖 Profile、events、材料、回答草稿、连接引用或语音模型。
保留旧包和数据备份可回退；有未保存代码时先保存。设置可打开实际数据、日志与下载目录。

## 已知限制与未验收项

- 本次发布没有进行新的真实 AI、麦克风或 macOS 用户实机验收；Windows 验收主机已有开发环境，不是全新虚拟机。
- macOS 15 CI 成功不等同于 macOS 14 或每款芯片用户实机通过，也不等于 Apple 公证。
- DeepSeek 高推理历史真实测试仍有仅思考无正文／传输失败，未宣称解决；失败后保留回答和重试入口。模型、账户及上游网络影响时延，不保证秒级回复。
- 语音权重单独下载，校准速度和准确率受硬件与音频影响；不提供云端服务或额度。
- 可选 PyTorch 不在便携包；缺少依赖的题显示限制，建议源码环境安装相应 extras。
- Field-tested runs 仍为 0；自动化与合成 UAT 不计作真实学习者证据。公开测试不是防作弊系统，本地执行器不是恶意代码沙箱。
