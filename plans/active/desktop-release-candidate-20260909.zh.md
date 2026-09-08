# 桌面候选版 ExecPlan · 2026-09-09

## 目标与可观察结果

在现有桌面功能上完成六项人工反馈，并交付可运行的 Windows x64 候选包、macOS arm64 CI 证据、公共题库覆盖、正式页面对照、性能与升级验证。仅候选分支；不推送 main、不打公开 Tag、不发布或覆盖 Release。所有数据为本轮 synthetic；不访问真实 Profile、材料、答案、密钥或历史 Oracle。

## 当前事实与保留基线

- 源目录：`E:/hz-llm-interview-lab-codex`。起始 HEAD：`cb3d13bba6368ee26a2efeb660f625e22b43edce`，起始分支 main。
- 工作分支：`candidate/desktop-release-20260909`，从当前带未提交改动的工作树原地分支，未丢弃任何修改。
- 必须保留的未提交产品基线：Zipformer 流式预览 + Qwen3-ASR 0.6B 停句校准、模型下载/许可和测试、相关文档/比较脚本；六项反馈的 Controller/QML/中文题面修改。
- 未知附件、`.uat-*`、临时 Controller 摘录、用户原始图标/反馈/计划不批量提交、读取或删除。新实验只放 `workspace/maintainer/release-candidate-20260909/`。
- 源码版本目前 `0.4.0a3`；发布 workflow 写死 alpha.3，正式 publish 有覆盖旧资产行为，需要改为显式门禁且拒绝覆盖。
- Windows：Python 3.11 虚拟环境；PySide6 6.11.2、Nuitka 4.2、sherpa-onnx 1.13.7、PyTorch 2.13.0 已存在；E 盘约 67 GiB 空闲。`gh` 未登录，继续通过已配置 SSH 验证 Git 推送；不能把未执行的 CI/实机验收说成通过。
- 旧报告中的测试数量不是本轮证据。当前中文 Practice 原先误用简短摘要；完整翻译中 OPT-005 旧 SHA 分支也误拦了已中文化原文，现已修正待最终定向验收。

## 范围与不做

保留 Qt Quick/ApplicationService/CLI；不重写 Controller、业务协议或历史数据。保留计时、模型选择、逐场授权、冻结问答、评分证据、运行/测试区别、No-AI、语音、IME、草稿、连接密钥环。仅用户主动检查/下载官方 GitHub Release，不自动安装。课程新增资产未获人工审查不得提升验证等级或算进发布覆盖。

## 里程碑与验收

1. **六项反馈与基线（进行中）**：可收起侧栏、移除左下档案装饰（设置保留切换）、宽屏自然布局、完整中英题面、恢复配置与 SHA 绑定的材料选择、启动自动连接。真实 QML 输入/点击/重启与四尺寸双主题字体检查。逐场发送确认保留，记住选择不是启动发送。
2. **可靠性与测量**：先测冷/热启动、知识首次打开/重复查询、长历史渲染/滚动、提交本地开销、工作集；冻结阈值后优化。实现 Profile/session/question/revision 绑定的防抖口述草稿、切页/退出/IME/写入失败恢复；审计已有代码/知识草稿。禁止草稿自动提交或改写锁定答案。
3. **公共内容与更新**：生成精确覆盖矩阵及随包清单；补发现筛选/关联入口；依缺口准备少量待审训练闭环资产。新增官方 Release 查询、版本渠道比较、后台下载/取消/校验/打开位置和错误重试；检查公共资源同步及旧 synthetic 数据升级。发布脚本版本统一、禁止未经门禁发布/覆盖。
4. **集成、构建、证据**：仅此时一次全量回归；Windows 完整构建和无开发环境依赖启动，中文空格路径/升级数据验证；推送独立候选分支运行现有 CI 的 macOS arm64 构建/Artifact 检查。整理包 SHA、测试/性能/内容/UI、发布与回退说明。为本阶段保留排期最后三分之一；不在收尾新增架构。

### 命令与证据位置

所有命令采用隔离数据目录、QSettings 与无真实凭证的测试 fixtures。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_desktop_resume_polish.py -q
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\llm-lab.exe doctor
.\.venv\Scripts\llm-lab.exe knowledge validate --with-catalog
.\.venv\Scripts\python.exe scripts/validate_external_courses.py
# 草稿、搜索、更新、发布脚本及受影响原有测试：随实现记录精确选择
# 最终一次：python -m pytest -q；CPU PyTorch 精确验证
# 现有 pyside6-deploy / check_desktop_artifact.py 与 build_macos_desktop.py / check_macos_artifact.py
git diff --check
```

正式视觉复核：900×620、1080×680、1280×800、1440×900 × light/dark × 100%/125%，另含 2560 宽屏；原生 Windows 中文字体。基线/After 都使用真实 Controller/QML + synthetic，不用 Phase 0 原型。采集环境、SHA、命令、图像 SHA 后才入公共证据。

## 性能指标（测量后冻结，暂未宣称优化）

同机相同 synthetic 公共资源，冷首次样本与后续热样本分开；每项至少 5 次，报告中位数/p95（小样本同时保留原始值），内存使用工作集。待基线确定常用热点后冻结目标；至少一个真实路径改善，其他关键路径无超过测量噪声的实质退化。不得以禁用校验/语音/状态恢复实现提速。

### 2026-09-09 已测基线与冻结阈值

`scripts/benchmark_desktop_candidate.py --samples 5`，真实 Windows QML / 1440×900 / 软件渲染；每次新进程和新 synthetic Profile，系统临时目录中的隔离公共资源。源 `b319934`；系统磁盘缓存未清除，首个样本不能冒充 OS 冷启动。结果位于本轮 ignored 目录 `performance-before.json`。

| 路径 | 基线中位数 | 冻结验收 |
|---|---:|---|
| 启动至点击侧栏成功 | 4434 ms（首次 6186 ms） | 中位数不增加超过 20% |
| 知识页首次打开 | 33.7 ms | 不增加超过 50 ms；资源已由正式启动路径加载的成本计入启动 |
| 连续搜索（含事件处理和 10 ms 布局 tick） | 42.2 ms，120 次查询 | 降低至少 25%，结果集合及排序完全一致 |
| 提交回答的本地保存 | 113.7 ms | 不增加超过 50 ms；不包含 AI 等待 |
| 40 轮问答加载 | 1356 ms | 不增加超过 20% |
| 滚动位置更新/事件处理 | 0.0083 ms | 仅事件处理量测，不称为 GPU 帧时延；不增加超过 2 ms |
| 最终工作集 | 289.9 MiB | 不增加超过 15% |

实际定位：UI 的 `ApplicationService.search_knowledge` 对每个 query token 重复 flatten 公共卡片。下一修改只缓存当前已验证知识快照的检索文本，保留查询 AND 语义、稳定顺序和公开文件变化后的失效/重新验证。

## 风险、回退与停止

- 当前真实应用进程与数据不触碰；测试仅新隔离目录。新代码引入自动连接，测试必须使用可控连接替身，不能读取系统真实 Keyring。
- 记住材料配置仅预填相同 ID/SHA；新场次仍检查并确认发送范围，变更/撤权不恢复授权。
- 新语音模型仅下载到用户缓存，不把已下载模型/个人录音打包或提交。
- 无 gh 登录不阻塞本地开发；SSH/公开 CI 证据不足时如实报告具体平台未通过，不绕过发布门禁。
- 回退使用候选提交的可恢复 revert 或保留完整旧包；不重写 main/历史，不覆盖用户数据。
- 核心交付未实测或平台门禁失败，结论必须为“尚不可发布”。时间耗尽不是完成。

## 决策日志

- 2026-09-09：用户新的候选目标允许独立分支/CI/最终全量/打包，覆盖先前本轮禁止构建、仅 main 的限制；仍禁止正式发布。
- 2026-09-09：在当前工作树创建候选分支，完整承接 STT 与反馈修改；不 checkout 旧版本，不动其他 worktree。
- 2026-09-09：中文题面使用完整显示层翻译/已中文原文，不改固定题契约与测试；原始英文仍可切换。

## 进度日志

- [x] 阅读目标与必读产品/架构/课程/发布上下文，检查 dirty baseline、工具和磁盘；创建候选分支。
- [x] 六项反馈的第一轮修改及定向复核：可折叠侧栏、移除底部档案块（设置保留切换）、宽屏面试和 Practice 布局、96 道完整中文显示、版本绑定材料偏好、启动 AI 恢复；材料仍逐场确认。
- [x] 未提交口述草稿绑定 Profile/session/question/题目 SHA 与文本 revision，600 ms 防抖、真实子进程重启、锁定回答优先、写盘失败阻止关闭并允许重试；知识练习增加防抖和退出前保存。
- [x] 性能基线、草稿恢复、性能改善与公共覆盖（源码证据，待包内核对）。
- [x] 更新功能及发布脚本/资源升级定向验证（真实 GitHub 成功查询仍待网络验证）。
- [ ] 最终回归、Windows 包实际启动、macOS CI/Artifact。
- [ ] 最终报告、包与校验、候选提交/推送和发布裁决。

## 最终复盘

待实际验证后填写；当前状态 `IN_PROGRESS / NOT_RELEASE_READY`。

### 2026-09-09 04:48 HKT 续接点

- 候选源代码 `4a987a7`，main 仍是 `cb3d13b`。保护并承接本轮开始时的已跟踪 STT/UI 改动；未知未跟踪反馈、原图及旧 UAT 目录均未纳入提交或清理。
- 唯一一次完整回归在 `c10f864` 完成：873 passed、19 skipped、51 failed、2 teardown errors（943 个独立测试；teardown 可附属于通过的测试）。不再次全量；失败清单逐项复查。已有 skip 是真实麦克风/模型 opt-in 或 Windows symlink 权限，不新增 skip/xfail。
- 已修复真实缺陷：材料摘要引用不存在的 QML ID；跳转 Codex 设置后目标字段仍在滚动区外；损坏锁定答案使整场会话无法打开；缺可选依赖时首页前几项均不可开始。原始严格 SHA/评分校验继续保留。
- 旧测试曾要求逐题先评分、为旧 Catalog 固定第一题或默认求职阶段。对照批准的 v2 协议和真实公共资产更新测试夹具；保留错误重试、不重复评分、原位代码执行、同一编辑器及中英切换断言。未削弱生产响应校验。
- 正式 Windows 平台下，四尺寸 × 双主题 × 100%/125% 的公共页面、首次使用及控件矩阵 8 passed；代码运行/结束评分、语言切换、面试配置和七页截图组合 12 passed。离屏插件产生方框字的那组图片作废，不作为公开证据。
- 源码原生 Windows UI Automation 已完成真实建档、代码保存、自造样例输出 9、公开测试明确失败（未实现完整题目）、退出、重启及同一档案/代码恢复；这是合成数据上的真实业务操作，不是真实麦克风或付费 AI。
- Windows `2cc62ad` 首个完整包通过既有 Artifact smoke，随后真实交互发现 Nuitka 主动排除 torch 时 find_spec 抛 ImportError，阻断建档。已在 `4a987a7` 修复并增加源码定向验证（3 passed，包含八岗位无依赖）；`2cc62ad` 包不可交付，保留为诊断证据。新包构建与原生首用复验进行中。
- 已解决 PySide6 6.11 长 Windows 命令临时入口与 Nuitka 输出目录不一致；增加实际 compiler report completion 检查，防止 PySide 返回 0 却交付半成品。不是通过关闭门禁来接受残缺包。
- 初次候选 CI `34265130218` 的 macOS 在测试步骤失败，未获得候选 macOS Artifact。公开 API 被限流、gh 未登录；只读取公开网页确认状态，不查找凭证。待推送修复后的独立候选分支触发新 CI，禁止 main/Tag/Release。

### 第二个候选切片

- 搜索优化安静环境复测 5 个新进程：连续查询中位数 42.19 → 24.51 ms（约 -41.9%）；启动 4434 → 4599 ms、40 轮记录加载 1356 → 1382 ms、结束工作集 289.9 → 291.3 MiB，均在预先冻结阈值内。包含 GPU 以外事件处理，不能称为帧率证明。
- 公共矩阵 254 节点：96 ready（84 Oracle / 12 contract），158 planned，24 retention-ready；开发机 84 道达到环境资格，包内是否可运行另验。知识卡 255。Profile/岗位仍会限制刷题列表范围，不等同于目录总数。
- NNL-018 两组延迟复测候选：18 个 public tests、12 随机种子的 60 个有限差分 VJP 和 24 个 CPU PyTorch VJP 检查通过；只保留 AUTHOR_PENDING_REVIEW，不进入 Catalog 或掌握证据。
- 更新模块使用固定 GitHub 来源，无令牌；主动检查/下载、预发布比较、取消、SHA 校验、不执行和不覆盖文件。Settings 原生 QML 验证四尺寸、两主题、两种字体缩放，网络使用显式替身。
- 代码/知识练习关闭保存和已有口述草稿保持分离；公共资源同步发生中断时旧版本标记保留，重启可重试，合成 Profile/events/草稿/材料/模型/设置保持逐字相同。
- 发现基线四项静态 QML 测试仍要求已消失的旧主页按钮/不再存在的永久工作区导航，且禁止基线已有的仅键盘快速操作；对照 cb3d13b 后更新断言并补真实键盘动作测试，未删除现有产品入口。另修正真实控件边界对比度不足，保持原最低对比度测试。
- 源码候选版本 0.4.0a4；发布只允许手动 workflow_dispatch + 既存匹配 Tag + 本轮全部测试/平台资产门禁，不覆盖 Release。当前不会创建 Tag 或发布。

### 当前定向证据与待查

#### 2026-09-09 06:35 HKT 续接

- 最终 Windows `2729e280` 包已构建并通过加强后的 Artifact 检查：181,570,046 字节，SHA-256 `6990867f0b18043b9c2c9d4818ddb93e963cda6192e158998d3a64c3e0758840`，位置 `dist/candidate-final-windows/LLMInterviewLab-Windows-x64-portable.zip`。641 个公共文件 SHA 全部与源码相符；包内覆盖仍为 27 道环境可运行验证题。
- 新的中文/空格路径和全新 synthetic-final 档案，PATH 不含 Python。原生窗口完成 FND-001 保存、脚本输出 2、17 个公开测试通过、提交实现、显示“开始自助复盘”；events 没有 task_mastered。关闭后重新启动，只有原档案、代码及待复盘状态完整恢复，侧栏仍收起。仅此处使用本轮 ignored 空间新写的 AUTHOR 验收实现，没有读取历史 Oracle 或真实学习者作答。
- 包内实际验证流式识别与 Qwen 0.6B ONNX 工厂及 NumPy/SciPy/soundfile 运行库可导入。未下载模型、未打开麦克风、未执行真实识别，不能据此宣称准确率通过。
- CI `34284301760` 的 macOS 为 942 passed / 1 failed / 8 skipped，未进入构建；剩余单个设置页测试在固定 80 ms 时读到中间态 36 px 宽度，没有 binding/polish loop 日志。只把测试改成最多 2 秒等待真实布局，保留边界、高度和主题/语言点击断言，并增加宽度与父布局一致断言。Windows 四尺寸直接复验 4 passed / 27.65 秒，macOS 仍须重新验证；未修改生产代码或以跳过测试放行。
- 同轮 Ubuntu 三 Python、Windows 3.11/3.12、CPU PyTorch、中文文档通过；Windows 3.10 核心及桌面构建仍在执行。新的文档/测试提交不改变最后生产来源 2729e280，无需为此重复本地打包。

#### 2026-09-09 06:44 HKT 证据补齐

- 最终生产源码安静环境五次性能复测已完成（HEAD d7791ee，仅测试/文档晚于生产来源 2729e280，tracked diff 为空）：搜索 42.19 → 25.12 ms（-40.47%），启动 +5.40%，40 轮加载 +2.61%，最终工作集 +1.46%；所有预先冻结阈值通过，120 次命中与排序逐项一致。首次进程 6793 ms，保留原始值和 p95，不挑选较快样本。
- 最终包打开 f0b173c 的旧合成数据，通过原生窗口返回旧题，代码逐字一致；Profile/events/submission 三份文件 SHA 与启动前相同。此前 4a → f0 的升级链也保留。均未触碰真实用户数据。
- 远端 34284301760 的 Ubuntu 与 Windows 三 Python 核心矩阵现均成功：Ubuntu 各 649 passed / 32 skipped，Windows 各 648 passed / 33 skipped；CPU PyTorch 2 passed，中文文档 28 passed。跳过项来自这些纯 dev job 未安装桌面/Torch 等可选依赖，非本轮新增跳过。
- 前一生产切片 9bebba5 的 Windows MSVC CI 已实际构建成功并通过 worker/隐私检查（83 个桌面目标测试通过），远端候选 Artifact 10079758302；最终 2729 生产切片的本地 MinGW 包已完成，当前 d779 CI 34286507207 继续核验平台。最后 macOS 结论未取得前，整体仍不可公开发布。

#### 2026-09-09 06:51 HKT macOS 运行时声明修正

- 最终发布说明审阅发现真实版本冲突：CI 使用 `pyside6-6.11.2-cp310-abi3-macosx_13_0_universal2.whl`，旧 plist、Nuitka 参数和安装指南仍宣称 macOS 12。对照 [Qt 6.11 官方支持范围](https://doc.qt.io/qt-6/supported-platforms.html#macos) 后，将候选最低系统统一为 13.0；保留旧 Alpha.3 的历史 12+ 说明，不降级依赖或声称在 12 上验证过。
- 仅修改 macOS 打包声明、对应 Artifact 断言、一个一致性目标及安装文档；直接目标 5 passed / 0.42 秒。没有修改应用逻辑、UI、Windows spec、公共课程或用户数据，因此最终 Windows 本地包、图片及性能仍对应同一应用源码，不需重建本地 Windows。
- macOS 必须使用修正后的构建来源获得 CI/Artifact；运行时声明为 12 的旧候选即使编译成功，也不作为最终 macOS 交付。

#### 2026-09-09 06:04 HKT 续接

- macOS 修复后全量为 939 passed / 3 failed / 8 skipped：两项 GridView 缓存 delegate 的异步生成未等待，一项已禁用的缺依赖关联题仍可通过直接 Controller 入口创建任务。未把失败改成跳过。
- 岗位测试改为最多 2 秒等待真实八个 delegate 完成，八项数量、非重叠、首/四/八点击和 CTA 断言保留。Controller 仅在新建练习时检查依赖；旧当前任务仍可恢复编辑，不改变 CLI 或题目元数据。新增定向测试确认拒绝创建时 events 不变。该测试初次把所有 Python 题也标成缺依赖，已修正为只模拟缺 PyTorch。
- 对应测试组合 19 passed，新增依赖恢复目标修正后 1 passed。顺便修正真实看到的输出标题为中性“执行输出”，正文继续区分脚本和公开测试；桌面指南修正遗留 a3 源码版本及过时构建命令，不宣称模型已在用户机器准备好。
- 下一步重建包含该入口修复的最终 Windows 包，补最后正式截图和 macOS/Windows core CI。只对实际发布阻断进行修改，不重新开始全量本地回归或视觉重写。

#### 2026-09-09 05:54 HKT 续接

- Windows `f0b173c` 构建完成并通过包含两个真实 worker 的 Artifact 检查。ZIP 为 181,568,542 字节，SHA-256 `2cc693b01e3f215ecb6a16d7a5a512bebb882f1875d89fcbee2b1a0adbf5e09a`。旧 2cc62ad / 4a987a7 失败包只保留诊断，不交付。
- 将 ZIP 解压到本轮全新中文/空格路径、移除 PATH 中的 Python，通过原生 Windows UI Automation 创建中文合成档案 → FND-001 → 保存非题解脚本 → 输出 9/退出 0 → 公开测试如实报 missing_symbol → 关闭 → 重启 → 一份 Profile/原代码/侧栏状态保持。No-AI 入口没有创建 Session。没有真实麦克风、模型调用或用户档案。
- 用新版包打开本轮 4a987a7 原生验收数据：档案、events、submission 三个文件 SHA 完全不变，原代码回到编辑器。首次比较误用了另一个 fixture 的空格格式，已改为和该旧档案自己的保存内容逐字核对，未修改档案来满足断言。
- 在包内执行公共覆盖脚本，确认 27 道已验证代码题具备运行环境；641 个公共文件与源码 SHA 无差异。不能用开发机 84 道代替包内资格。
- 最终原生 Windows 矩阵 8 passed / 65.58 秒；IME/口述及知识草稿组合 8 passed / 55.90 秒。截图源及像素契约 1 passed。Windows 真机截图已人工查看首页、准备、回答、代码、报告、连接及设置，未见新增重叠/裁切。
- 最终安静五进程性能源 9bebba5（生产源码与 f0 相同）已通过冻结阈值：搜索 -40.81%，启动 +6.75%，长记录 +3.03%，内存 +1.60%。原始样本保留并公开；滚动 p95 6.31 ms 仅事件处理，不声称帧率。
- CI 34281371924 的 Ubuntu 三 Python、CPU PyTorch、文档通过；Windows 桌面测试通过并在构建，macOS 正在测试。Windows core 三矩阵在旧 12 分钟总 Job 限额被取消，日志未出现测试失败；只将该任务限额调整为 35 分钟，不减少测试、不修改超时行为的业务契约。
- 剩余低优先级：Practice 输出面板沿用“公开测试输出”标题，但脚本正文明确标注脚本执行/退出码及“不构成测试通过”，本轮原生验证已如实区分结果。可在下一次纯视觉更新收敛为中性执行标题，不据此声称本轮已彻底统一所有文案。

#### 2026-09-09 05:23 HKT 续接

- 唯一全量失败清单逐项重跑：54 passed；截图/仓库文档契约组合：118 passed。不重跑全量。
- `4a987a7` 包完成并通过原 Artifact smoke，真实原生操作可创建中文合成档案并打开 FND-001；保存正常，但无 Python 路径下脚本/Grader 启动失败。因此此包仍不可交付。
- 已直接读取本轮合成应用进程的两个运行变量确认：Nuitka 将 `sys.executable` 指向未随包交付的 `python.exe`。`f0b173c` 改用正在运行应用的 argv[0]，增加已有脚本业务的私有 worker 分派，同时明确打入 pytest 动态插件。Windows/macOS Artifact 检查现在实际执行 stdin → stdout 和 pytest/unittest 子进程，不能仅以窗口 smoke 放行。新增相关目标组合 24 passed。
- 新建仅安装 dev 的隔离环境复现 CI 缺 httpx：补充 dev 依赖后 660 项成功收集；DeepSeek/worker/release 定向 24 passed。无 Torch 环境的 45 项面试/内容目标验证通过：不可运行题明确排除，流程记 coding 缺口，不改生产选题资格或分数。
- macOS `34276888730` 原始结果为 926 passed / 12 failed / 8 skipped，未进行构建。现在可使用已有 GitHub 连接读取日志（gh 仍未登录），不需要用户凭证。按具体失败修复紧凑页面的宽度来源、连接表单重排定位和展开面试配置后的字段可达性；Windows 对应 14 passed，连接精简后的复查 8 passed。macOS 修复仍须远端重新验证。
- 正式截图重新取自 `f0b173c`，七页双主题 7 passed。Before 保持 cb3d13b 历史源码，未篡改旧图。Windows 新包正在构建，输出目录 `dist/candidate-workers-windows`。
- 使用生产下载器实际从官方 GitHub 下载 Alpha.3 历史 Windows 包（只下载，不启动、不安装），99,776,341 字节，SHA-256 `ff67ae6564808b7f8aa5109dc3e9cf559e2307b813d1605ab732464f99d01150` 与官方清单一致，20.63 秒；重复调用重新校验并复用。当前 a4 尚未公开，实际新版发现成功仍不能声称完成；公共 API 限流错误已单独记录。

- 六项反馈测试初轮 8 passed；草稿/重启/偏好组合 7 passed；本地 STT 与知识测试 27 passed / 2 skipped（既有实际模型/录音环境要求未满足，不是新增跳过）。928 tests collected 为实现中快照，非最终测试总数。
- 所有上述网络动作是受控替身，无真实凭证、麦克风或付费 AI 调用；正式 Windows QML 截图仅证明布局，不证明 AI 已连通。
- 性能脚本将新 fixture 放在仓库嵌套 E 盘路径时出现 Qt 原生访问错误，定位在 QSettings 同步附近；单独 QSettings 及定向测试通过。改用系统临时目录后连续 5 个新进程完成；这不是根因证明，仍需检查 E 盘/打包入口。正式应用使用系统 QSettings，而非此脚本的 INI 覆盖。没有修改生产序列化或编辑器实例来掩盖错误。
