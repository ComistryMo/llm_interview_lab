# Product V1 编程工作台视觉方向

## 2026-09-09 人工反馈修订（v1 正式版设计）

产品正式版本统一为 v1.0.0，之前的 Alpha 编号属于开发期。本次只改版本和文档，不更改应用界面；原截图的来源、日期和 SHA 保持不变。[v1 发布说明](../release-notes-v1.0.0.md)记录下载与使用限制。

已在正式页面调整：顶栏提供可记忆的侧栏收起按钮，移除左下档案装饰（设置保留档案切换）；面试整体宽度随大窗口增长至 1200，短问题和回答区自然相接，长历史仍独立滚动。Practice 题面分栏按可用宽度扩大，默认呈现完整中文要求，不再把列表摘要当题面。颜色与现有 Graphite Blue 组件不变。

定向验证使用真实 Controller/QML、隔离 synthetic 档案与连接替身；未使用真实简历或 AI。8 项反馈检查已通过，七页双主题 Before/After 共 28 张正式图片已整理到[候选视觉证据](desktop-candidate-20260909.zh.md)。最终四尺寸、双主题、100%/125% 布局组合 8 passed，中文组字与草稿组合另有 8 passed。不用截图冒称 AI 或 macOS 用户实机验收通过。完整候选进度见[ExecPlan](../../plans/active/desktop-release-candidate-20260909.zh.md)。下面的 2026-09-08 和 Phase 0 内容保留为历史事实。

> 决策状态：`VISUAL_DIRECTION_SELECTED_GRAPHITE_BLUE`。Graphite Blue 已冻结为生产主方向；本文件中的六张图仍是 Phase 0 合成原型和历史设计证据，不是正式业务页面。

> Phase 0 原型评审稿。六张图使用同一份合成中文题面、代码和测试用例，生成于 `scripts/capture_product_v1_visual_directions.py`。原型只验证信息层级与视觉气质，不代表已实现的编辑器、Grader 或面试状态。

## 统一内容与边界

原型内容为 `LOSS-014 · Masked Cross Entropy`，固定呈现：

- 左栏：题目说明、输入 Shape、约束、示例、H1–H3 提示和相关题；
- 右上：`submission.py`、行号、代码编辑器、运行样例/正式验证/AI 解析动作；
- 右下：Case 01、Case 02、全 Padding 边界、输入/期望/执行结果；
- 状态只使用“未保存”“尚未运行”“不形成正式掌握证据”等真实语义，不展示通过率、提交次数或虚构指标；
- 题面、代码和测试输出使用不透明实色；磨砂/高亮只用于顶栏、工具栏、选中标签和状态胶囊；
- 原型不读取 Profile、Catalog、Private Tests、Oracle 或用户文件，全部内容均为 `synthetic: true`。

## 六张方向图

### Graphite Blue

![Graphite Blue 浅色](../images/product-v1/graphite-blue-light.png)

![Graphite Blue 深色](../images/product-v1/graphite-blue-dark.png)

### Obsidian Violet

![Obsidian Violet 浅色](../images/product-v1/obsidian-violet-light.png)

![Obsidian Violet 深色](../images/product-v1/obsidian-violet-dark.png)

### Warm Frost

![Warm Frost 浅色](../images/product-v1/warm-frost-light.png)

![Warm Frost 深色](../images/product-v1/warm-frost-dark.png)

## 对比

| 方向 | 信息密度与对比度 | 长时间阅读 | 品牌辨识度 | QML/跨平台成本 |
| --- | --- | --- | --- | --- |
| **Graphite Blue** | 深色代码区和低饱和蓝色焦点最清楚；浅色层次稳定，分栏边界明确 | 很好，蓝色只作为动作和焦点色，长文本不染色 | 高。与 Quiet Forge 现有蓝色资产连续，也有成熟开发工具气质 | 低。可复用现有 `AppTheme` 的冷中性色；Windows/macOS 一致性高 |
| **Obsidian Violet** | 深色层次柔和，紫色选中态容易形成“氛围”；浅色对比需要更谨慎 | 中上。长时间使用时紫色面积应继续收窄，避免视觉疲劳 | 最高。比通用蓝更有独立品牌记忆点，但过量会接近装饰性 AI 产品 | 中。需要额外检查不同显示器的紫灰对比和无障碍状态色 |
| **Warm Frost** | 浅色题面最舒适，暖灰表面对分栏友好；深色需要维持足够边界对比 | 最好，适合长题面、复盘和材料阅读；代码区仍应保持冷/中性实色 | 中上。安静、专业、偏编辑器/研究工具，不会抢内容注意力 | 低到中。系统主题适配简单，但暖色状态与系统深色模式要单独校准 |

## 与 Codex / Claude Code 类生产力工具的差距

当前原型已借鉴成熟工具的几个结构性特征，而不是复制品牌：

1. **工作上下文优先。** 题面、代码和 Case 在同一 SplitView，工具栏只保留当前动作；没有把聊天面板永久挤进主工作区。
2. **操作层级清晰。** “运行样例”是唯一高强调动作；“正式验证”和“AI 解析”保留边界，不伪装成已经可用的结果。
3. **状态可见但不喧宾夺主。** 未保存、Revision、尚未运行和本地模式均在靠近对象的位置表达，而不是用全局 Toast 覆盖内容。
4. **实色承载长文本。** 代码和题面没有透明/模糊背景，避免阅读和截图中的对比度损失。
5. **仍有差距。** 生产级版本还需要真实编辑器的语法高亮、光标/选择、保存状态和 Diff/Approval；本原型没有宣称这些能力已经完成。

## 推荐决策

**推荐主方向：Graphite Blue。** 它在三项硬约束之间最平衡：代码与题面可读性、深浅主题对比、Windows/macOS 的低风险一致实现。建议吸收：

- 从 Graphite Blue 采用冷中性表面、细分隔线、蓝色焦点环和单一主 CTA；
- 从 Warm Frost 借用浅色长文本区域的暖灰微差，以及更克制的圆角和阴影；
- 从 Obsidian Violet 只借用“低饱和紫蓝作为少量选中/品牌细节”的思路，不把紫色扩散到代码正文、错误和大面积背景。

## 已冻结的生产规则（DEC-001）

- 主体采用 Graphite Blue：冷中性表面、细分隔线、低饱和蓝色焦点环、单一主 CTA。
- 浅色主题的长题面、知识解析、材料和报告区域吸收 Warm Frost 的暖灰微差；代码编辑器继续使用冷中性不透明实色。
- Obsidian Violet 只用于极少量品牌细节、选中状态和 AI 辅助强调；不得用于代码正文、错误状态、长文本区域或高饱和渐变。
- 磨砂只用于侧栏、顶部工具栏、Command Palette、Dialog、Toast 和少量浮层。题面、代码、测试结果、Transcript 和长文本必须保持不透明实色。
- Phase 2 仅把规则应用到首用入口、设置、No-AI 锁定说明和首题路径的层级/布局修复；不会把原型静态状态接入正式业务。

**不建议现在做：**

- 在用户选定方向前批量替换现有所有 QML；
- 为原型引入新的设计系统、动画、模糊插件或 WebView；
- 把截图中的静态动作误接到 Grader 或 Provider；
- 以截图代替真实 Windows/macOS 可用性验收。

## 原型实现与证据

- QML：`src/llm_interview_lab/desktop/qml/prototypes/ProductV1WorkbenchPrototype.qml`
- 捕获脚本：`scripts/capture_product_v1_visual_directions.py`
- 证据清单：`docs/images/product-v1/manifest.json`
- 生成命令：

```powershell
py -3.11 scripts/capture_product_v1_visual_directions.py --settle-ms 220
```

每张图为 1280×800，内容合成且不含个人材料。用户选择方向后，下一阶段再将经过确认的 token 逐步吸收到正式 Coding Workbench。

## 2026-09-08 正式 UI 统一（基线 `6a1fd20`）

本次按用户批准的“统一、克制、内容优先”计划升级正式页面，以上六张原型继续仅作历史证据。
边界是表现层：不改变业务入口、默认配置、材料授权、面试协议、模型、评分或计时。

### 设计规则

- 复用 `AppTheme`，标题／分区／正文／长题面／辅助文字／代码依次为 24／18／14／15／12／14，随原有字体缩放。
- 普通控件圆角 8、弹窗 12、回答容器 16；基准高度 40，放大文字后按字体度量自然增高。
- 标签、正文和辅助说明分层，长复选框标签换行；焦点和中文组字期间隐藏提示，焦点描边不改变尺寸。
- 表单宽度 720、阅读宽度 760、列表宽度 1000；实色承载长文本，低饱和蓝只强调焦点与链接。
- 参考 [OpenAI UI 指南](https://developers.openai.com/plugins/concepts/ui-guidelines) 的有限字号与稳定间距、[Claude Code 桌面指南](https://code.claude.com/docs/en/desktop-quickstart) 的就近操作，以及 [Linear](https://linear.app/changelog/2024-03-20-new-linear-ui) 和 [shadcn/ui Sidebar](https://ui.shadcn.com/blocks/sidebar) 的层级组织；不复制品牌或引入其技术栈。

### 分批实施与检查

1. 公共控件、导航、首页、首次使用：统一 Basic 控件外观、移除首页大卡片，岗位卡按文字缩放增加高度而非压缩字号。四种尺寸首用布局、首／第四／第八岗位点击、提示隐藏和原生标准弹窗接受动作均有定向检查。
2. 面试、代码与报告：统一准备／记录页签，收起配置后主动作跟随摘要；回答区由四行增长至页面高度的 40% 再内部滚动；报告使用换行标题与短动作；编辑区去除外层重复边框。四尺寸深浅主题与 100%／125% 的准备、代码、报告定向检查通过，长回答光标跟随、独立滚动、稳定提交位置、中文组字和上下文弹窗保持可用。录音 UI 测试只把过期的批量转录 mock 改成流式 mock，未修改语音业务。
3. 刷题、知识、进度、材料、连接、设置：统一字体与表单组件，取消固定高度证据容器，按自然内容高度排版；材料导入保留可见标签和完整授权说明；连接与 Codex 使用一致的行宽和动作，No-AI 仅作简短说明；设置改为轻分区。保存、删除确认、模型设置跳转仍调用原入口。

Windows 离屏插件未正确渲染中文字体，其截图不作为视觉验收证据。正式对照使用 Windows 原生 Qt 平台和隔离合成 Profile，不读取真实材料，不调用付费模型。

### 两轮视觉复核与修正

- 第一轮：统一控件与字号后检查正式页面，进一步收紧准备页空白、表单宽度、报告长标题和复选框换行。使用 `LabText.strong` 统一字重，避免子页的 `font.bold` 与组件 `font.weight` 同时设置。
- 第二轮：修正连接表单错误说明越界、放大字体的确认弹窗高度，以及宽屏代码区“几何存在但未实际绘制”的问题。代码区保留唯一编辑器并固定在同一滚动容器，小窗口切换显示区域，不再在两个活动视口之间重新挂载。验证了编辑器像素、对象身份、切换后的草稿和真实脚本运行，不仅检查空容器边界。
- 辅助文字对比度已调整；浅／深主题四种普通文字 token 对六种不透明表面均达到 4.5:1，蓝色焦点对这些表面均达到 3:1。该检查不等同于所有语法高亮与禁用态的完整无障碍认证。
- Markdown 修改仅限显示：防止移除 Qt 点制字号后又触发过大的默认 HTML 标题。题面、代码内容及接口没有改写。

### 正式页面 Before / After

Before 加载只读 `6a1fd20` 工作树的正式 QML；After 加载本轮正式 QML。两者使用同一测试场景定义及真实隔离 Controller，不使用 Phase 0 原型或 demo controller。档案名称、计时秒数和视口位置可能不同，图片用于布局比较，不是逐像素性能基准。

全部示例回答、Session 和报告证据均由本地测试建立，没有连接真实 AI。图中 No-AI 状态与测试场景并存，不作为真实连接或面试解锁成功的证据。首次使用截图单独从无档案的真实启动状态采集。

| 页面 | Before | After |
| --- | --- | --- |
| 首页 | [浅色](../images/ui-unification-20260908/before-home-light.png) · [深色](../images/ui-unification-20260908/before-home-dark.png) | [浅色](../images/ui-unification-20260908/after-home-light.png) · [深色](../images/ui-unification-20260908/after-home-dark.png) |
| 准备面试 | [浅色](../images/ui-unification-20260908/before-setup-light.png) · [深色](../images/ui-unification-20260908/before-setup-dark.png) | [浅色](../images/ui-unification-20260908/after-setup-light.png) · [深色](../images/ui-unification-20260908/after-setup-dark.png) |
| 回答区 | [浅色](../images/ui-unification-20260908/before-answer-light.png) · [深色](../images/ui-unification-20260908/before-answer-dark.png) | [浅色](../images/ui-unification-20260908/after-answer-light.png) · [深色](../images/ui-unification-20260908/after-answer-dark.png) |
| 代码区 | [浅色](../images/ui-unification-20260908/before-coding-light.png) · [深色](../images/ui-unification-20260908/before-coding-dark.png) | [浅色](../images/ui-unification-20260908/after-coding-light.png) · [深色](../images/ui-unification-20260908/after-coding-dark.png) |
| 报告 | [浅色](../images/ui-unification-20260908/before-report-light.png) · [深色](../images/ui-unification-20260908/before-report-dark.png) | [浅色](../images/ui-unification-20260908/after-report-light.png) · [深色](../images/ui-unification-20260908/after-report-dark.png) |
| AI 连接 | [浅色](../images/ui-unification-20260908/before-connections-light.png) · [深色](../images/ui-unification-20260908/before-connections-dark.png) | [浅色](../images/ui-unification-20260908/after-connections-light.png) · [深色](../images/ui-unification-20260908/after-connections-dark.png) |
| 设置 | [浅色](../images/ui-unification-20260908/before-settings-light.png) · [深色](../images/ui-unification-20260908/before-settings-dark.png) | [浅色](../images/ui-unification-20260908/after-settings-light.png) · [深色](../images/ui-unification-20260908/after-settings-dark.png) |

补充：[无档案首用浅色](../images/ui-unification-20260908/after-onboarding-light.png)、[深色](../images/ui-unification-20260908/after-onboarding-dark.png)；[900×620／125% 连接错误浅色](../images/ui-unification-20260908/after-connection-error-900-125-light.png)、[深色](../images/ui-unification-20260908/after-connection-error-900-125-dark.png)。

32 张正式图片及其尺寸、SHA-256、源码指纹见 [证据清单](../images/ui-unification-20260908/manifest.json)。常规对照逻辑尺寸为 1280×800、100% 字体；实际 PNG 尺寸随 Windows 显示缩放变化，不将物理像素误写成窗口逻辑尺寸。中间诊断与第一轮图片留在 ignored 维护目录，不加入公共仓库。

### 实际执行的定向验证

测试使用 `QT_QPA_PLATFORM=windows`、`QT_QUICK_BACKEND=software` 和隔离临时数据。以下记录各组最终定向结果，不把重复运行次数相加，也不是全量回归结论。

| 测试文件与选择范围 | 实际结果 |
| --- | --- |
| `test_ui_visual_unification.py`：`test_page_text_and_controls_fit_all_display_modes` | 6 passed；六个页面各覆盖四尺寸 × 两主题 × 两字体比例，共 16 种显示组合 |
| 同文件：`test_fresh_onboarding_at_all_display_modes`、`test_refresh_confirmation_fits_large_text` | 各 1 passed；无档案首用覆盖 16 种组合，确认弹窗覆盖 900×620／125% |
| 同文件：`test_theme_text_and_focus_contrast`、`test_shared_controls_keep_native_input_and_dialog_contracts` | 2 passed；文字／焦点对比、复选框、开关、键盘数字步进和确认弹窗信号 |
| `test_unified_interview_ui.py` 三项 | 3 passed；准备／记录、代码和报告的尺寸矩阵；编辑器切换不丢草稿，知识链接可达 |
| `test_ui_visual_unification.py`：`test_production_page_gallery` | 7 passed；七个正式场景分别采集浅／深主题 |
| 同文件：Markdown 标题、真实代码运行、连接字段错误三个单项 | 各 1 passed；实际脚本输出 `9`、退出码 0，未把脚本运行标为公开测试通过；错误文本可见且可重试 |
| `test_interview_input_runtime.py`：回答 IME、长回答滚动、长上下文弹窗 | 5 passed；焦点／组字／提交文本提示隐藏、内部滚动和稳定提交位置 |
| `test_desktop_polish_ui.py`：录音状态四场景 | 4 passed；使用流式转录替身验证 UI，不声称本轮完成真实麦克风或语音模型测试 |
| 模型设置跳转、设置保存、已保存 Key 修改／删除确认 | 3 passed；只使用测试连接与测试密钥存储替身 |
| 首页真实入口、连接行与动作 | 6 passed；包括小窗口及放大字体 |
| 单次提交进入下一问、保存失败、缺少 consent、取消／超时、切档草稿、简历与 JD 授权 | 8 passed；传输采用可控替身，不作真实 Codex／DeepSeek 成功声明 |
| `test_onboarding_qml_hotfix.py`：岗位列表与首／第四／第八项点击 | 定向通过；保持显式选择、原创建入口和重复点击门控 |

这些都是实际运行的目标用例。命令形式为 `.venv\Scripts\python.exe -m pytest tests/infrastructure/<文件>.py::<上述用例> -q`；多项按需同次指定。仅修正已过期的测试夹具：下一问响应补当前协议要求的 `coverage`、语音 mock 使用已有流式接口、首页断言匹配基线已有路由。没有为使测试通过而修改生产协议。

交付前静态检查通过：32 张图的 SHA／尺寸、26 个表现层源码指纹、本文与桌面指南的本地链接，以及 `git diff --check`。源码指纹是交付状态快照；清单明确记录工作树采集，不冒充来自干净提交的截图。

未运行：完整 pytest、付费模型请求、RC CI、Windows/macOS 打包或发布、macOS 实机与真实系统输入法候选窗人工验收。中文输入验证使用 Qt 输入法事件，并非声称人工遍历了每一种输入法。DeepSeek 高推理传输问题未在本轮修复。

### 交付与边界复核

三个实现批次均已完成。修改仅涉及 QML、公共样式、两个结构图标、Markdown 显示字号、目标测试及文档证据；未改 Provider、面试协议／Prompt、评分／计时、材料授权、语音模型、Catalog 或 Mastery。

保留原有私人 UAT 目录、未跟踪反馈和原始附件；不纳入本轮提交。源码提交使用 `[skip ci]`，仅推送 `main`，不创建 Tag／Release。下一步是用户对当前源码页面进行人工视觉验收；本轮停止于此，不扩展业务功能。

## 2026-09-09 · 源码预发布补充

本轮不是全面 UI 改版。只在原连接表单增加分阶段错误和「复制脱敏诊断」，在原设置页增加增量更新的安装确认；继续使用已有公共组件。当前为 `1.0.1a1` 源码预发布，用户选择暂不打包，日常用[源码启动入口](../desktop-app.md#源码运行)测试。

正式 QML 的 1080×680 Windows 点击证据：[连接错误与复制诊断](../images/source-alpha1/connection-diagnostic-1080.png)、[设置中的安装确认](../images/source-alpha1/update-install-confirmation-1080.png)，[清单](../images/source-alpha1/manifest.json)记录实际源提交与图片 SHA。错误、Profile 和已准备更新状态均为隔离合成测试数据；确认弹窗截图不证明安装包已完成真实更新。没有访问真实 Key 或调用付费模型。

原 `candidate-20260909` 截图仍保留 v1.0.0 时的源码与图片校验，不回写成当前截图。本轮未验证 macOS 实机、原生安装包、全尺寸 UI 或真实系统密钥环；这些边界与早期发布记录分开。
