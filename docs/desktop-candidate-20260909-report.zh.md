# 2026-09-09 桌面候选验收报告

状态：**候选验收进行中，尚不可发布**。Windows 本地实际包已通过执行和原生首用流程；远端矩阵及 macOS 构建结论尚待补齐。没有推送 main、创建 Tag、覆盖旧 Release 或正式发布。

## 1. 范围、源码与数据边界

- 仓库 `ComistryMo/llm_interview_lab`，本地 `E:\hz-llm-interview-lab-codex`。
- 候选分支 `candidate/desktop-release-20260909`；起点/main 为 `cb3d13bba6368ee26a2efeb660f625e22b43edce`。起点已有的 tracked 流式语音/UI 改动一并保留在 `b319934`，没有从旧源码重建而遗漏近期功能。
- 最终 Windows 本地包及正式截图的应用源码为 `2729e280d75273df55cdc5e61e3828ea07b1d258`。性能复测来源 `d7791ee21dfd8d3a17edfd9ac3e09729d3c6c107`；后续只调整测试/文档及 macOS 最低系统声明，Windows 应用、公共课程及界面源码未变。包内 `runtime_assets/BUILD-METADATA.json` 保存准确来源及文件 SHA。
- 未知未跟踪的反馈、计划书、原图、`test结果.md`、`题目.md`、旧 UAT 目录和临时文件没有被打包、提交、清理或读取。用户原先运行的应用及其数据未触碰。
- 本轮只使用新建 synthetic 档案、题面公共资产、自己生成的运行探针和可控传输替身；公开测试通过路径的 AUTHOR 验收实现仅放在本轮 ignored 空间。没有读取真实简历、录音、API Key、系统密钥或历史维护者 Oracle。

可续接进度、失败尝试及每轮修正见 [ExecPlan](../plans/active/desktop-release-candidate-20260909.zh.md)。

## 2. 六项反馈与配套升级

| 用户问题 | 当前结果 |
|---|---|
| 放大后布局空、阅读和作答分离 | 正式面试宽度随窗口扩展，短题/回答紧邻；代码区利用剩余空间，长历史仍可独立滚动 |
| 左下档案块冗余 | 移除装饰性档案块；实际档案切换保留在设置 |
| 侧栏不能收起 | 顶栏提供展开/收起，状态持久化；原生包关闭重启后已复验 |
| 中文只有摘要、英文完整 | 96 道 ready 资产默认完整中文显示，保留英文切换；接口、约束、测试与历史 fingerprint 不改变 |
| 重复填写面试及材料配置 | 同 Profile 恢复岗位、难度、时长、AI 配置及未变化材料；ID/SHA 不符或撤权后不复用。记住材料不是永久发送许可，新场次仍确认实际范围 |
| 启动后反复手动连接 | 自动恢复上次连接，使用原模型/推理设置，不发送材料；成功/失败原位显示。凭证测试使用替身，没有冒称本轮真实 DeepSeek/Codex 登录成功 |

新增口述和知识回答本地防抖草稿：中文组字期间不写入半成品，绑定 Profile/session/question/revision，重启恢复不提交、不评分。代码保持现有显式保存、离开/关闭确认，不能宣称突然断电能恢复未保存代码。

搜索按已验证公共文件版本缓存检索文本；刷题增加合理的难度及环境筛选；设置新增匿名官方 GitHub 更新检查、下载、取消、SHA 校验和打开位置。更新不自动执行文件、不覆盖旧应用或用户数据。

## 3. Windows 实际候选包

本地 ZIP：`dist/candidate-final-windows/LLMInterviewLab-Windows-x64-portable.zip`。

- 源码：`2729e280d75273df55cdc5e61e3828ea07b1d258`
- 大小：181,570,046 字节
- SHA-256：`6990867f0b18043b9c2c9d4818ddb93e963cda6192e158998d3a64c3e0758840`
- 入口：解压后的 `LLMInterviewLab/LLMInterviewLab.exe`
- 同目录校验清单：`SHA256SUMS-Windows.txt`

该包使用 Python 3.11.9 / PySide6 6.11.2 / Nuitka 4.2 / MinGW x64 构建，没有附带语音模型权重或 PyTorch。缺依赖会明确说明，不伪装成所有题可运行。

实际 Windows 原生操作使用 UI Automation 的 Invoke/Value（不是伪 Controller 或 screenshot state）：

1. 解压到本轮新建的中文及空格路径，去掉 PYTHONPATH/PYTHONHOME，PATH 只留 Windows 系统目录。
2. 从没有 Profile 的正式首次页面创建中文名称的 `synthetic-final`，选择 AI 产品岗位，打开完整中文 FND-001。
3. 输入并保存本轮新写的 AUTHOR 验收实现。点击运行代码，实际得到 `2`、退出码 0，正文明确说明这不是公开测试或掌握证据。
4. 点击公开测试，实际得到 `17 passed`；再点击“提交实现”，界面进入“开始自助复盘”。events 为实际运行、提交及 implemented，没有 task_mastered。
5. 收起侧栏、正常关闭、重启。同一个 Profile 自动恢复，没有重复建档；回到当前任务后代码逐字一致，待复盘状态仍在。
6. 前一 `f0b173c` 实际包另已验证非题解脚本输出 `9`，公开测试明确报 `submission_error:missing_symbol`，No-AI 面试不创建 Session；最终包的两个真实 worker 再次通过 Artifact 检查。
7. 用最终包打开本轮 `f0b173c` 旧候选合成数据，Profile/events/submission 三个文件 SHA 均未变化，编辑器恢复旧代码；此前 `4a987a7` → `f0b173c` 的同项升级也已验证。

以上证明没有依赖 PATH 中的 Python，但宿主机器本身安装了开发工具，**不是全新 Windows 虚拟机验收**。没有录制真实麦克风。新版启动数据边界、中断重试及模拟材料/语音缓存保持，另外由直接集成测试覆盖。

此前 `2cc62ad`、`4a987a7` 包在首次建档或执行入口上失败，仅作为 ignored 诊断保留，不是可交付版本。`f0b173c` 是可用的上一候选 checkpoint，最终交付使用 `2729e280`。Artifact 检查已加强为实际执行 script/pytest 两个 worker，不能只凭窗口 smoke 放行。

### Windows CI 的独立构建证据

[MSVC Artifact 10080687734](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34284301760/artifacts/10080687734) 来源 `aed507c`（与本地最终包的应用源码相同），已下载到 `dist/candidate-ci-aed507c/windows/`。内层便携 ZIP 为 172,108,415 字节，SHA-256 `0a74d986f6306fdac4c942ef674ba41a6dc9b933963177668d3896f8877fb0b4`，与生产方清单相符；GitHub 外层 Artifact ZIP 摘要为 `0b7c92acdb16ca354851a8ff6c7400b5a3d933730f64605d4d09173f975c9396`，两者不能混用。

这份实际下载的包也解压到新中文/空格路径，移除 Python 路径后用原生窗口创建 `synthetic-msvc`，进入完整中文 FND-001，保存并运行非题解探针，得到 `9`/退出 0；公开测试如实返回 missing_symbol。没有读取开发机 Profile 或凭证。MSVC 与 MinGW 产物大小、SHA 不同是不同工具链的实际结果，不宣称二进制可重复构建。

## 4. 视觉、内容和性能

- [正式 Before/After](design/desktop-candidate-20260909.zh.md)：7 个页面 × 两种主题 × 前后，共 28 张。来源和文件 SHA 在 manifest；未使用 Phase 0 图冒充。
- 最终 900×620、1080×680、1280×800、1440×900 × 深浅 × 100%/125% 布局组合 8 passed；输入/IME/草稿组合另有 8 passed。已人工查看实际 Windows 截图；不等于 macOS 用户实机排版验证。
- [公共覆盖](content/release-candidate-coverage-20260909.zh.md)：254 节点，96 ready（84 Oracle、12 contract）、158 planned，255 知识卡、258 来源、24 retention-ready。
- 641 个公共文件随包 SHA 与源码一致；包内运行同一覆盖脚本确认 **27 道**已验证代码题具备环境资格，开发机有 Torch 时为 84 道。不把 planned、缺依赖或未解锁当成可练。
- NNL-018 两组 D+2/D+7 AUTHOR 资产已完成 18 个公开目标验证、60 个有限差分 VJP 和 24 个 CPU PyTorch VJP 检查，仍是 `AUTHOR_PENDING_REVIEW`，不计入已准入覆盖。
- [最终性能数据](performance/desktop-candidate-20260909.zh.md)：5 次新进程，连续搜索 42.19 → 25.12 ms（-40.47%），命中/排序一致；启动 +5.40%、40 轮加载 +2.61%、内存 +1.46%，在预先冻结阈值内。原始值及 p95 保留，不承诺未知机器的秒级速度。

## 5. 测试与真实传输口径

没有反复在本地跑全量。唯一一次完整回归在 `c10f864`：873 passed、19 skipped、51 failed、2 teardown errors；随后按实际失败与影响范围修订、逐项复验，不把旧失败藏掉。

| 直接证据 | 结果 |
|---|---|
| 唯一全量的失败清单逐项复验 | 54 passed；旧参数化病例展开后数量变化，未减少断言 |
| 截图/仓库文档契约组合 | 118 passed；最终新图片 SHA 再核对 1 passed |
| 新版打包 worker / runtime / 发布边界组合 | 24 passed |
| 纯 dev 隔离环境收集 | 660 collected，修正缺失的 httpx 开发依赖 |
| 纯 dev、无 Torch 的内容/逐问轨迹 | 45 passed，不降低候选环境资格 |
| 最后一次四尺寸布局组合 | 8 passed / 65.58 秒 |
| 最后一次 IME、口述/知识草稿 | 8 passed / 55.90 秒 |
| 紧凑连接及异步恢复复验 | 8 passed / 54.97 秒 |
| 新建缺依赖练习/旧题恢复直接目标 | 1 passed；只阻止缺依赖的新任务，不丢旧代码 |
| 最终正式页面截图采集 | 7 passed / 47.02 秒；与生产源码 SHA 一致 |
| 设置页四尺寸实际布局与点击 | 4 passed / 27.65 秒；补稳定帧等待，保留全部几何断言 |
| 双语 README 与文档入口复验 | 25 passed / 21.06 秒 |
| Windows 包 Artifact 检查 | PASS，含 stdin/stdout、pytest/unittest、版本、事件循环、公共资产及隐私边界 |

`doctor`、知识与 Catalog 验证、外部课程验证、CPU PyTorch 和内容精确验证均在本轮执行并记录于 ExecPlan。上述组合有重叠，不相加伪造测试总数。既有真实模型/硬件/符号链接条件的 skip 保留，没有为本轮新增 skip/xfail。

真实更新传输：通过生产下载器从本仓库官方 GitHub 下载历史 Alpha.3 Windows 包，99,776,341 字节，20.63 秒；SHA `ff67ae6564808b7f8aa5109dc3e9cf559e2307b813d1605ab732464f99d01150` 与官方清单一致，重复请求校验并复用。仅下载、不安装或执行。匿名发布查询遇到公共出口限流，展示具体错误并可打开官方发布页面；没有声称本轮真实发现尚未发布的 Alpha.4。

真实 Codex/DeepSeek、多轮远程付费模型、麦克风及 macOS 用户实机均**未运行**。对应异步流、失败、重试、取消、授权及本地 STT 接口使用合成输入和可控替身，不混称真人实测。最终包内实际导入 NumPy/SciPy/soundfile/sherpa，并验证流式识别、Qwen 0.6B ONNX 工厂及运行库可用；未下载模型或执行识别，不能声称准确率已验收。

## 6. CI、发布与回退

当前 [候选 CI 34288557804](https://github.com/ComistryMo/llm_interview_lab/actions/runs/34288557804) 验证 `4f939695ce0d411356f6121ea46e5569018366a2`。前一 `d7791ee` 轮 macOS 整套测试已通过并进入构建；更早 `34284301760` 的六个核心 Python/系统矩阵、CPU PyTorch、文档及 Windows 构建均通过，macOS 留下的一个固定 80 ms 布局等待失败已修正，未减断言。Windows core 旧 12 分钟限额延长至 35 分钟，没有减少测试。

最终 macOS 包要求 Apple Silicon / **macOS 14+**。CI 实际安装 Qt 的 13+ wheel 和 NumPy/SciPy 的 14+ Accelerate wheel，不能仅按 Qt 写 13，也不能沿用 Alpha.3 的 12+ 声明。`4f93969` 同步编译参数、plist 和 Artifact 检查为 14；仅更改元数据不能证明在较低系统兼容。仍使用 ad-hoc signing，无 Developer ID、无公证，macOS 15 CI 不能代替用户实机验收。

源版本 `0.4.0a4` / 预期发布 Tag `v0.4.0-alpha.4` 只用于一致性校验，不代表 Tag 或 Release 已创建。[发布说明与安装步骤](release-notes-v0.4.0-alpha.4.md)保留候选状态。

用户审阅后如需发布，现有工作流要求手动 publish、匹配已存在 Tag、本轮全部测试和两个平台 Artifact 通过；禁止覆盖旧 Release。Windows 解压到新目录再切换入口，macOS 退出后替换 app；保留旧包及原数据目录可回退，不删除 Profile、events、材料、草稿、密钥引用或模型缓存。

剩余事项：补齐最终远端核心与 macOS 平台门禁，核验候选 macOS 产物；公开发布前仍应做目标机器麦克风/真实模型及 macOS 交互验收。Practice 输出标题已统一为“执行输出”，正文明确区分脚本退出码与公开测试结果。另有不阻断执行的 P2 文案：结果尾部“测试版本”实际显示的是被测作答摘要 `tested_revision`，后续可改为“作答版本”；不为这一标签再次重建本轮 Windows 包。
