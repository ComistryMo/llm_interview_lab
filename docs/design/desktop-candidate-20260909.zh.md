# 桌面候选版：真实界面与交互证据

状态：本轮布局与输入检查完成，候选技术门禁通过，等待用户审阅。这些是正式 `AppController` / `Main.qml` 的隔离合成档案，不是 Phase 0 原型。画面中的本地未完成面试和草稿真实持久化；没有真实模型、麦克风或私人简历传输，不能以截图证明 AI 已连通。平台包与未验收事项见[候选报告](../desktop-candidate-20260909-report.zh.md)，没有公开发布。

## 本轮可见变化

- 顶栏增加侧栏收起/展开按钮，并保留选择；左下角档案卡移除，档案切换仍在设置。
- 面试短题的回答框紧跟正文，宽屏正文和编辑区域随可用空间增长，不再由固定高度撑出大块间隔。长历史仍可滚动，不自动把正在阅读历史的用户拉到最新。
- 固定练习默认完整中文题面，包含接口、约束、例子和评价要点；原文可切换。只改变显示，不修改题目的接口、测试、fingerprint 或历史冻结内容。
- 口述草稿显示本地保存状态；写盘失败可重试，恢复不会提交答案或自动发送给 AI。
- 刷题增加编码难度及当前环境筛选；设置增加版本检查、下载和校验入口。

面试准备保留配置和未变更材料选择。材料 ID / 源文件及文本 SHA 必须匹配；撤权或内容变化不会复用授权。新场次仍确认实际发送范围。

## Before / After

两侧使用相同的正式测试夹具流程：真实本地建档、动态开场、草稿编辑、进入真实代码题、结束为 incomplete，以及真实页面导航。网络发现关闭以避免接触真实凭证。没有注入“已连接”或“评分通过”。

| 场景 | 修改前 | 候选版 |
|---|---|---|
| 首页 · 浅色 | [Before](../images/candidate-20260909/before/home-light.png) | [After](../images/candidate-20260909/after/home-light.png) |
| 准备面试 · 浅色 | [Before](../images/candidate-20260909/before/setup-light.png) | [After](../images/candidate-20260909/after/setup-light.png) |
| 回答区 · 深色 | [Before](../images/candidate-20260909/before/answer-dark.png) | [After](../images/candidate-20260909/after/answer-dark.png) |
| 手撕区 · 浅色 | [Before](../images/candidate-20260909/before/coding-light.png) | [After](../images/candidate-20260909/after/coding-light.png) |
| 报告 · 深色 | [Before](../images/candidate-20260909/before/report-dark.png) | [After](../images/candidate-20260909/after/report-dark.png) |
| 连接 · 深色 | [Before](../images/candidate-20260909/before/connections-dark.png) | [After](../images/candidate-20260909/after/connections-dark.png) |
| 设置 · 浅色 | [Before](../images/candidate-20260909/before/settings-light.png) | [After](../images/candidate-20260909/after/settings-light.png) |

每个场景均另有相反主题，完整 28 张图片的文件 SHA、真实像素尺寸、来源 commit 和生产源码摘要见 [manifest](../images/candidate-20260909/manifest.json)。逻辑窗口为 1280×800，文字缩放为 100%；本 Windows 环境原生截图为 1920×1200（系统像素比例 1.5），不是把图片放大生成的。

采集修改前的真实源码为 `cb3d13bba6368ee26a2efeb660f625e22b43edce`，独立只读 worktree；没有以新版 Controller 搭配旧版 QML 冒充旧产品。候选来源以 manifest 为准。历史 Alpha.3 截图及其旧版本信息保留，不换写当前 SHA。

## 复现与判读

在对应源码 checkout 使用隔离目录运行：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:QT_QPA_PLATFORM = 'windows'
$env:QT_QUICK_BACKEND = 'software'
$env:PYTHON_KEYRING_BACKEND = 'keyring.backends.null.Keyring'
$env:LLM_LAB_UI_EVIDENCE_DIR = '<本轮新的合成截图目录>'
python -m pytest tests/infrastructure/test_ui_visual_unification.py -k production_page_gallery -q
```

`scripts/write_candidate_evidence.py` 只接受这七个命名场景，复制图片并记录来源摘要；不能用它把旧截图宣称为新源代码截图。当前候选截图契约会核对像素文件和实际生产源文件是否一致。

图像复核已覆盖默认状态、短题、代码长签名、incomplete 报告和连接缺失态。布局矩阵、中文 IME、保存、取消、重试和后台状态另由真实 Qt 定向测试验证，结果在候选报告汇总；截图不能替代这些交互测试。macOS 实机排版不在本机截图证明范围。
