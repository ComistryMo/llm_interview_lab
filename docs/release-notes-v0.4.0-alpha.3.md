# v0.4.0-alpha.3：真实交互与可靠训练

这是一个 Alpha 预发布版本，重点修复桌面端首次使用和日常训练中的真实交互问题。

## 本次更新

- 岗位选择卡片改为明确的可点击布局，支持小窗口和清晰的选中状态；
- 首次创建学习档案时提供可操作的中文错误提示，No-AI 模式无需任何外部服务；
- 练习页默认收紧布局，移除无法发送的假聊天控件，并保留真实 AI 教练入口；
- 运行测试前保存当前编辑器内容并绑定 revision，避免测试旧答案或串题；
- Windows 提供 standalone portable ZIP，便于定位运行时资产和启动错误；
- macOS Apple Silicon 提供 `.app.zip` 和 `.dmg`，完成架构、启动和隐私检查；
- 使用 Quiet Forge 项目图标，并刷新中文桌面截图证据。

## 下载

| 平台 | 文件 |
| --- | --- |
| Windows 10/11 x64 | `LLMInterviewLab-Windows-x64-portable.zip` |
| macOS Apple Silicon（macOS 12+） | `LLMInterviewLab-macOS-arm64.dmg` |
| macOS Apple Silicon 直接解压 | `LLMInterviewLab-macOS-arm64.app.zip` |
| 完整校验清单 | `SHA256SUMS.txt` |

## 签名与限制

- Windows 包未使用商业代码签名；
- macOS 包使用 ad-hoc signing，未使用 Apple Developer ID，也未经过 Apple Notarization；
- 本版只提供经过验证的 Apple Silicon arm64 包，不宣称 Intel 或 Universal2 支持；
- Profile、Submission、求职材料、API Key、Oracle、Private Tests 和 Git 历史不进入发布包；
- Grader 只用于执行用户本人信任的本地代码，不是恶意代码沙箱；
- AI 服务不可用时仍可使用 No-AI 本地训练；
- 真实 Field Runs 继续按实际值记录，当前为 0。

下载后请先使用 `SHA256SUMS.txt` 校验文件，再按 [Windows 指南](windows.md) 或 [macOS 指南](macos.md) 操作。
