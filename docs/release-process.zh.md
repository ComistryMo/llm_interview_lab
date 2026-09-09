# 桌面版发布与旧开发版整理

## 本次发布结果（2026-09-09）

- [v1.0.0 · 首次正式发布](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0)已公开，非 Draft、非预发布，也是 GitHub Latest；Release 列表现仅保留这一版。
- Windows ZIP、macOS APP ZIP／DMG 及三份 SHA 清单均已上传。三个包的公开 SHA 与[固定清单](../.github/release-manifest.json)完全一致；两平台包内产品版本均为 1.0.0。
- [发布工作流](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34313638291)全部成功，版本标签指向 `325693ad4c63d1f646a06f510363ed216a8abea5`；应用构建源与测试来源仍是下文的 `8fe697c`。
- 七个旧开发版 Release 页面及附件已移除。原始说明和全部附件先备份、核对 SHA，再完成删除；[备份 Artifact](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34313638291/artifacts/10089292480)约 1.82 GB，保留至 **2026-12-08**，到期后自动过期。
- 旧 Git 标签和提交历史完整保留。用户现存未提交文件、真实档案、材料、Key、录音与语音权重没有被清理或上传。

本机已通过 Actions 下载两平台原始 Artifact，并逐包核对 SHA 和包内版本。发布后的 GitHub 元数据也确认六份资源均为 uploaded，三个包的 digest 与本地文件一致。但本机对三个公开下载地址的直连 HEAD 检查遇到连接重置／30 秒超时，因此不宣称本机公网直连下载成功；这与构建或上传失败不是同一项检查。

## 版本约定

产品从 **v1.0.0** 开始正式发布。源码版本为 `1.0.0`，Git 标签为 `v1.0.0`，GitHub Release 不标记为预发布。

此前的 0.x / Alpha 是开发期编号。旧截图、测试记录与源 SHA 保留真实信息；更名不代表这些测试重新执行，也不改变已知限制。当前用户说明以 [README](../README.md) 和 [v1 发布说明](release-notes-v1.0.0.md) 为准。

## 本次构建

本次版本修改触及包内显示及构建元数据，因此从 `8fe697cb8f0d25cac7e963fc466d6703526be610` 重新构建 Windows x64、macOS arm64，不能改名复用旧包。

[本次构建与验证](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34305123396)使用现有 CI，包含核心检查、中文文档、PyTorch 专项、双平台构建与产物检查。首次构建尝试因一条旧测试强制 README 包含 CLI 长命令而失败；已把命令示例保留在面试指南，测试核对相应链接与指南，未改变应用或 CLI 行为。当前链接为修正后的构建，后续仅文档和发布清单的提交使用 `[skip ci]`，不重复打包。

本次还发现一项 GUI 自动化时序问题：测试在切换页面后立即执行第二次坐标点击，可能早于 QML 完成布局。仅在该测试的两次页面变化后各等待 100 ms，保留原点击与断言；应用代码未变。该定向测试在 Windows 离屏环境通过（1 passed，94 deselected）。同一构建源的 macOS 作业单独重跑后通过：960 passed，8 skipped；Windows 和其他已经通过的作业没有再次执行。

实际构建源、Artifact ID 和三个包的 SHA 固定在 [release-manifest.json](../.github/release-manifest.json)。本次 CI 的 10 个必需作业均已通过，后续发布仍需逐包校验。实际发布状态和剩余限制以本版说明为准。

## 实际验证范围

- Windows CI：83 项桌面定向检查通过；standalone 启动、代码及公开测试 worker、压缩包与隐私边界检查通过。
- macOS 15 arm64 CI：960 passed，8 skipped；APP 启动、ad-hoc 签名、ZIP 和挂载 DMG 检查通过。
- Ubuntu／Windows 的 Python 3.10、3.11、3.12 核心检查、CPU PyTorch 专项、中文文档作业均通过。
- 本地文档／版本／截图复用定向检查：23 passed；发布晋级检查：14 passed；旧 CLI 文档链接检查：1 passed；页面布局等待修正：1 passed；中文与链接检查：2 passed。这些是分别执行的目标检查，不包装成额外一轮全量回归。
- 本次没有新增真实模型付费测试、麦克风识别测试、macOS 用户实机验收或全新 Windows 虚拟机验收；没有重拍 UI 截图。README 使用的正式页面图片保留原来源信息。GitHub 页面的浏览器视觉复核因浏览器工具启动失败未执行；已完成 Markdown 链接与结构检查。

## 发布顺序

1. 版本与文档先提交到 main，完成一次构建及对应验证。
2. 核对实际产物与校验值，更新发布清单；确认 Tag、源码版本与 Release Notes 一致。
3. 创建版本 Tag，触发 [publish.yml](../.github/workflows/publish.yml)。只接受 main 上的提交和通过完整门禁的构建。
4. 下载清单中精确的 Artifact，校验构建方 SHA 和人工固定的 SHA；应用、依赖或构建输入改变时拒绝复用旧包。
5. 建立 Draft，上传 Windows ZIP、macOS APP ZIP、DMG 及三份校验清单，全部上传成功后公开。
6. 公开后核对版本、非 Draft、非预发布、下载文件与 SHA，再执行下面的旧开发版整理。

GitHub CLI 本地未登录时，通过已授权的 Git 推送和仓库工作流令牌完成发布；不查找个人凭证或读取学习档案。

## 一次性整理旧 Release

用户在 2026-09-09 明确要求清空旧 Release。仅处理已核对的七个开发版：

- v0.4.0-alpha.4、v0.4.0-alpha.3、v0.4.0-alpha.2、v0.4.0-alpha.1；
- v0.3.0-alpha.1、v0.2.0-alpha.2、v0.2.0-alpha.1。

工作流仅在本次 `v1.0.0` 发布时执行此操作。先保存各版 Release JSON 与所有原始附件，逐一核对 GitHub 登记的 SHA，再上传 `development-releases-before-v1` 备份 Artifact，保留 **90 天**。

备份失败不执行删除。删除前再次确认 v1 已公开、六份资源齐全，旧 Release ID 与预期标签一致。只删除这七个 Release 页面及其附件，**不删除 Git 标签、不重写提交历史、不触碰用户数据**。开发期文档保留历史事实，但不再作为当前下载入口。

备份 Artifact 有保留期限；需要长期保留旧二进制时应在过期前下载。旧发布说明同时保留在 Git 历史与维护者本地发布清单中。

## 发布后的核对

- README、英文 README、Windows/macOS 指南与源码均指向 v1.0.0。
- GitHub Release 为首次正式版，不再展示旧开发版 Release。
- exe、APP 的版本和 BUILD-METADATA 来自真实的 1.0.0 构建。
- 签名、PyTorch、语音、高推理及未完成实机验收等限制保留；正式版不等于“没有缺陷”。
- 升级只替换程序，不删除档案、材料、答案、Key、录音或语音模型。

旧开发期发布与验收记录见[变更日志](../CHANGELOG.md)及[历史候选报告](desktop-candidate-20260909-report.zh.md)。
