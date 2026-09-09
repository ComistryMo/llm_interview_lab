# 已验收桌面产物的发布

本流程用于将**已经完成候选验收的原始包**公开发布，不修改应用、不反复打包，也不以文档 CI 替代应用验证。

## Alpha.4 来源

- 原始构建源：`4f939695ce0d411356f6121ea46e5569018366a2`。
- [完整构建 CI 34288557804](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34288557804)：六组核心矩阵、CPU PyTorch、中文文档、Windows 与 macOS 桌面全部通过。
- 固定源、产物 ID 和发布文件 SHA：[release-manifest.json](../.github/release-manifest.json)。
- 原生操作与剩余限制：[候选报告](desktop-candidate-20260909-report.zh.md)。

## 发布操作与门禁

维护者获得发布授权，先把文档和验证变更合并到 main，再创建与源码版本一致的版本 Tag。新建 Tag 触发 [publish.yml](../.github/workflows/publish.yml)，不是普通分支 Push 自动发布。

工作流检查：

1. Tag 在 main 历史上，版本、release notes 与清单一致。
2. 清单中 CI 来自本仓库可信 Push／手动构建，精确源 SHA 的十个技术 Job 均成功。
3. Tag 相比构建源只增加允许的文档、测试与发布文件；任何应用、课程、依赖或构建输入变化必须重新构建验收，不能复用旧包。
4. 只下载固定 Artifact ID，先核对构建方校验清单，再核对人工验收固定的三份 SHA。
5. 先建立 Draft、上传全部三份包和三份校验清单，再设为公开；已有 Release 不覆盖，不使用 force push。

该工作流使用 GitHub 的 `create` 事件，允许文档提交使用 `[skip ci]`，避免仅为整理文档重复跑完整构建。发布门禁仍核对原始完整 CI，并不跳过应用测试。旧 CI 中“手动 all + publish”的同次构建发布入口保留兼容，同样需要明确选择已存在 Tag，不能覆盖已发布版本。

本地没有登录 gh 也不影响经 Git 推送 Tag 后使用仓库工作流令牌发布；不搜寻个人凭证、不读取用户 Keyring。

## 发布后的核对

确认 Release 非 Draft、Alpha 标记保留，六份资源可下载且大小/SHA 与固定清单相符。Tag 的文档整理提交与包的构建 SHA 分别记录，不改写包内 BUILD-METADATA。
文档包含已知限制：未公证、未验收实机范围、便携包缺可选 PyTorch、语音权重单独下载及高推理历史失败。不能把“已发布”描述成“没有缺陷”。

下一版本需要更新真实构建源、产物 ID、SHA 与对应证据；不得只改版本字符串复用旧二进制。
