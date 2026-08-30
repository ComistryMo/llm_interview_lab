# main 合并交接与普通用户全局审阅（2026-08-30）

> 给接手 Codex 的结论：远端 `main` 已包含 Alpha3 桌面体验、真实状态修复、研究型面经知识层、题目资产、测试和截图，但当前 **不应视为可发布的 Alpha3**。先修复 CI、下载入口和首次可达性，再做内容扩张或视觉打磨。

## 1. 本次交接的范围

本报告回答两件事：

1. `main` 到底已经合并了什么，哪些提交和文件是事实来源；
2. 站在第一次下载、第一次建档、第一次刷题和第一次模拟面试的普通用户角度，项目还存在哪些阻断和优化机会。

本轮审阅只读取公开仓库、合成截图、固定 Catalog、Role Profile、CLI/ApplicationService 和 GitHub Actions 日志；没有读取真实 Profile、材料、答案、Transcript、Secret 或 Private Tests，也没有修改训练状态。

## 2. Git 与发布事实

### 2.1 对账锚点

| 项目 | SHA / 状态 | 说明 |
|---|---|---|
| Alpha3 UX 分支交付 | `85d4786f8e83d9b33ac6810899af1e4705046053` | 用户侧桌面打磨基线 |
| 内容分支末端 | `31887b2` | 岗位技能参与知识检索 |
| 两条工作线的本地合并 | `30798ab` | Alpha3 UX + 面经内容，双父非强制合并 |
| 本地发布前集成锚点 | `0f5a1bce77d6391bf96254df1cbfe1376d7f92d1` | 保留 106 个细粒度本地提交历史 |
| GitHub 内容快照提交 | `77f46de2818777bae381630928b731669c703544` | 文件树与上述本地集成结果等价；通过 Git Data API、`force=false` 发布 |
| 审阅开始时远端 `main` | `4f09623233adf3a76a09a64cc78dba1c9fa26a94` | 在内容快照后补充发布记录 |
| 本地远端历史对账合并 | `7359926` | 将远端两个快照提交合回本地细粒度历史；仅用于继续维护 |

远端 `main` 的内容已经发布，但 GitHub 上采用的是“内容等价快照”，不是逐个重放 106 个本地提交。因此：

- 新 clone 直接以 `origin/main` 的文件树为准；
- 不要为了“补齐历史”把 106 个提交再次 cherry-pick 到远端；
- 本地看见 `0f5a1bc` 与远端 SHA 不同不代表内容丢失；
- 禁止 force push 或重写 `main`；后续改动从最新 `origin/main` 新建分支。

### 2.2 已合并的产品能力

| 领域 | 已合并内容 |
|---|---|
| 首次使用 | 两步 Onboarding、显式岗位选择、No-AI 默认路径、可操作错误态 |
| 桌面 Shell | 响应式侧栏、Command Palette、Light/Dark、小窗口布局、八个页面状态和 64 张合成截图矩阵 |
| 刷题训练 | 固定 Catalog/DAG、公开测试、契约审查、口述、D+2/D+7、真实 mastery 边界 |
| Coach | Profile-local 多会话、恢复/删除、发送/停止/重试/复制、Context Preview、异步身份隔离 |
| 模拟面试 | 岗位蓝图、回答锁定、暂停/恢复、超时、Transcript、coding SHA/Grader 校验、证据化评分 |
| AI 边界 | AI 不修改答案、不授予 mastery；No-AI 与本地确定性流程独立可用 |
| 面经知识层 | 63 张卡片、65 条精选来源、191 条广泛研究登记；CLI/API/Learn 浏览与岗位准备包 |
| 新增手撕资产 | `VLM-007` 多模态 label mask、`PT-016` invalid completion、`INF-003` continuous batching scheduler |
| 深度研究 | VLM/视频与 grounding、后训练/RL、Agent/RAG/推理系统三篇研究附录 |

关键入口：

- `src/llm_interview_lab/application.py`
- `src/llm_interview_lab/cli.py`
- `src/llm_interview_lab/desktop/controller.py`
- `src/llm_interview_lab/desktop/qml/pages/*.qml`
- `curriculum/catalog/*.yaml`
- `curriculum/interviews/knowledge.yaml`
- `curriculum/interviews/blueprints.yaml`
- `curriculum/roles/profiles.yaml`
- `curriculum/skills/ontology.yaml`
- `references/interview-sources.json`
- `docs/research/*_deep_dive.md`
- `docs/images/screenshot-manifest.json`

### 2.3 现在没有完成的事情

- GitHub 尚无 `v0.4.0-alpha.3` tag 或 Release；公开 Release 只到 `v0.4.0-alpha.2`。
- 远端 `main` 最新两次 CI 均失败，当前 badge 应为红色。
- 229 个 Catalog 节点中仍有 184 个 `planned`；“有知识卡”不等于“有可运行练习”。
- 当前环境没有 PySide6，本轮没有把静态 QML 审阅冒充为原生桌面动态验收。
- 尚未在原生 Windows 11 和 macOS 窗口完成最终真人首次使用验证。

## 3. 当前内容与验证快照

### 3.1 内容规模

| 指标 | 当前值 | 普通用户应如何理解 |
|---|---:|---|
| Catalog 节点 | 229 | 全部规划范围，不等于全部可做 |
| Ready | 45 | 其中递归前置真正可达约 42 |
| Planned | 184 | 只能作为路线/未来内容说明 |
| Oracle | 33 | 有独立参考验证的可运行资产 |
| Retention-ready | 24 | 有 D+2 / D+7 复测资产 |
| 连续 Golden Quest | 3 | 目前都集中在基础训练 |
| Knowledge cards | 63 | 40 八股、17 手撕契约、6 面经模式 |
| 卡片级来源 | 65 | 用于具体 claim 追溯 |
| 广泛研究来源 | 191 | 含 24 条面试问题信号 |
| 固定非代码面试题 | 26 | 多个岗位/轮次候选仍只有 1 个 |
| 岗位蓝图 | 24 | 8 岗位 × 3 求职阶段 |
| Skills | 70 | 其中 15 个没有 `related_problems` |

### 3.2 已执行验证

本轮在无 PySide6 的当前容器中执行了非 Qt 受影响测试：

```text
115 passed in 53.67s
```

覆盖：Repository Contract、Knowledge、Application Service、Role Interview、Windows startup hotfix。PySide6 相关测试因依赖缺失不能收集或运行，已明确标注，未伪报通过。

此前合并切片的定向证据包括：Application/Knowledge 17 passed、AI 24 passed、Mock Interview 82 passed、Role Interview 25 passed、Catalog/Repository 76 passed。它们证明受影响切片曾通过，但不能替代远端当前 CI。

### 3.3 远端 CI 当前失败证据

审阅时远端 `main` 为 `4f096232...`，对应 [CI run 33320073117](https://github.com/ComistryMo/llm_interview_lab/actions/runs/33320073117) 失败；前一个内容快照 [CI run 33319989455](https://github.com/ComistryMo/llm_interview_lab/actions/runs/33319989455) 也失败。

已从 Actions 日志确认：

1. 通用 Python 矩阵在 `pytest --collect-only` 失败。Ubuntu 3.11 的直接原因是 `tests/infrastructure/test_alpha3_truthful_ux.py` 无条件导入桌面 Controller，而 core 安装不含 PySide6：`ModuleNotFoundError: No module named 'PySide6'`。
2. Windows Desktop：`4 failed, 55 passed`。四个失败均捕获到 `LearnPage.qml:429:33: Unable to assign [undefined] to bool`；当前位置是 `visible: parent.detail.title`。
3. macOS Desktop：`6 failed, 463 passed, 1 skipped`。除同一 QML bool 警告外，两个 symlink 安全测试收到“Profile path is outside workspace/profiles”，与测试期待的 `link|reparse|invalid` 稳定错误语义不一致。
4. Chinese docs 与 CPU PyTorch jobs 通过。

因此当前结论必须是：**功能已合并，发布门禁未通过。**

## 4. 普通用户视角的整体评价

### 4.1 做得好的地方

- “本地优先、AI 可选、确定性事实源”表达清楚，且主要按钮状态总体与后端真实能力一致。
- 两步 Onboarding 比早期工程化 CLI 更接近普通用户；No-AI 不再是隐藏的降级路径。
- Exercise、Interview、Coach 的职责边界清晰；AI 不代写、不授予掌握是可信的产品差异。
- 一次一题、答案锁定、计时、Transcript、Grader 与 Rubric 分离，模拟面试比普通聊天机器人更有训练价值。
- 知识卡有来源、claim 和 clean-room 约束，研究广度已经覆盖 VLM、后训练、Agent 和推理系统。
- 题库明确区分 ready/planned/oracle/retention，而不是用题目数量掩盖完成度。

### 4.2 普通用户当前会卡在哪里

| 用户旅程 | 正向体验 | 当前摩擦 |
|---|---|---|
| 下载 | README 首屏有 Windows/macOS 桌面下载与源码入口 | Alpha3 下载链接 404，用户第一步即中断 |
| 建档 | 两步完成，No-AI 可跳过连接 | 选 AI Agent Engineer 后可能没有任何可开始任务 |
| 学习 | 首页有继续训练，练习状态真实 | 45 个 ready 中 3 个被 planned 前置锁死；岗位主线普遍不连续 |
| 知识库 | 63 张卡可搜索、可追溯 | 来源不可点击，缺岗位筛选；卡片到关联练习没有直接闭环 |
| 编程题 | 编辑器、公开测试、复测边界明确 | 900×620 首次进入默认隐藏题面；通用算法/Tokenizer/GPU/CV 几乎全 planned |
| 模拟面试 | 单题专注、证据和计时清楚 | 选完组合才知道不可用；无 PyTorch 时算法/推理岗无法开始任何组合 |
| 回访 | Coach 会话与 Interview 可恢复 | 已评分 Rubric 重开显示“未评分但不可再评”；已掌握题无法回看 |
| 调整目标 | 有 8 类岗位画像 | 桌面端不能修改目标岗位、阶段和自评，推荐与 readiness 难以校准 |
| CLI | 功能覆盖广 | 新旧面试命令并存、help 信息弱、重复 quickstart 会静默改岗位 |

## 5. 发布前 P0：必须先解决

### P0-1：恢复绿色 `main`

建议最小修复：

- 让 core test collection 不依赖 PySide6：桌面测试使用 `pytest.importorskip`、测试级条件导入，或从通用 collect job 中按明确 marker 隔离；不能靠给所有 core 环境强装桌面依赖掩盖边界。
- 将 `LearnPage.qml` 的可见性表达式显式转换为 bool，并为 knowledge detail 为空补回归测试。
- macOS symlink 拒绝继续保持安全，但统一稳定 reason code 或错误文案；测试不要依赖偶然的 pathlib 文案。
- 先重跑失败的 collect/Windows Desktop/macOS Desktop jobs，再只跑一次完整 CI。

验收：3.10–3.12 × Ubuntu/Windows collection 全绿；Windows/macOS Desktop 全绿；CI badge 绿色；无新增跳过来隐藏失败。

### P0-2：修复不存在的 Alpha3 下载入口

`README.md` 与 `README.en.md` 显式链接 `v0.4.0-alpha.3` 下载页，平台文档也按 Alpha3 资产和行为编写，但 GitHub 没有该 tag/release。

二选一：

1. 完成 CI 和原生 smoke 后创建 Alpha3 tag/Release，上传 Windows 与 macOS 真实资产及 SHA-256；Linux 明确保持源码安装，不承诺当前 CI 没有产出的桌面包；
2. 在发布准备完成前把所有下载入口回退到 Alpha2，并明确 Alpha3 功能只在源码 `main`。

验收：所有下载链接 HTTP 200；文档列出的资产真实存在；版本号、文件名、平台范围和校验值一致。

### P0-3：保证每个首次选择的岗位至少有一个可开始任务

实测新 Profile 选择 `ai_agent_engineer` 后，Dashboard `unlocks=[]`、`current=None`。原因是该角色只有 `required_tracks: [agent]`，但入门前置在 `ai_foundation`；Catalog 又按 required tracks 严格筛选。

建议：

- 给 Agent 角色纳入 `ai_foundation`；或
- Planner 对岗位路线计算跨 Track 的前置闭包，并把“先完成基础路线”作为可解释推荐。

验收：8 个岗位 × 首次建档均至少返回一个可运行入口；首页显示推荐原因，点击“开始训练”能真正打开题目。

### P0-4：消灭“ready 但不可达”

当前三个新资产被 planned 前置永久锁住：

- `VLM-007` → `VLM-006`（planned）
- `PT-016` → `PT-008`（planned）
- `INF-003` → `ALG-007` + `INF-002`（均 planned）

建议实现最小前置，或调整依赖/状态；再增加仓库契约：任何 `ready` 节点的递归硬前置必须可达。UI 同时显示锁定原因和替代路径。

验收：45 个 ready 全部从至少一个起点递归可达，或不满足者不再标 ready。

### P0-5：修正永远到不了 100% 的岗位准备度

`ApplicationService.dashboard()` 目前只按 Skill 的 `related_problems` mastered 比例计算 verified readiness：70 个 Skill 中 15 个没有题目映射，分母还包含 planned/不可达题。AI 产品经理 10 项核心技能中 7 项没有代码验证入口。

在“当前 42 个可达 ready 全部 mastered”的理想假设下，按现公式估算的 new-grad verified 上限仍为：

| 岗位 | 当前可达上限 |
|---|---:|
| AI 产品经理 | 0.0% |
| AI 应用工程师 | 21.5% |
| AI Agent 工程师 | 24.1% |
| AI 算法 / 研究工程师 | 63.1% |
| 后训练工程师 | 41.7% |
| AI Infra / ML 平台 | 16.1% |
| AI 推理 / 系统工程师 | 14.4% |
| AI 评测 / 数据 / 安全 | 5.4% |

这不是用户能力上限，而是当前验证资产和公式造成的产品上限。

建议：

- 把单一 readiness 拆成“已评测技能掌握率”和“岗位技能评测覆盖率”；
- 代码题、固定面试 Rubric、项目证据和人工审核使用不同 verified evidence 类型；
- 没有验证资产的 Skill 显示“未评测”，不要显示为能力 0；
- UI 显示当前版本 attainable ceiling，避免虚假的低分或虚假的满分。

验收：完成全部可用证据后，“已评测技能掌握率”可以达到 100%，但“岗位技能评测覆盖率”仍如实显示剩余缺口；产品不得把低覆盖率重新归一化成“岗位准备度 100%”。

### P0-6：让“PyTorch 可选”与模拟面试行为一致

无 PyTorch 环境实测中，`ai_algorithm_research_engineer` 与 `ai_inference_systems_engineer` 在 intern/new-grad/mid × easy/medium/hard 全部不可开始，因为必须的 coding round 报 `missing_environment=['pytorch']`，即使口述和项目题已有候选也被整体阻断。

建议：

- 提供明确标识的“无代码轮降级面试”，不伪装为完整蓝图；或
- 在岗位选择和 Interview setup 前置展示 PyTorch 依赖、大小和一键安装/诊断路径；
- 默认选择首个可用组合，并显示每轮候选数、缺题、环境、替代难度。

验收：无 Torch 用户能完成一次明确标注的非代码模拟面试，或从 GUI 一步到达可执行的安装修复方案。

## 6. P1：下一轮最值得做的用户价值

### P1-1：先做岗位纵向闭环，不再横向铺 184 个 planned

三条连续 Golden Quest 都是基础能力。优先让每个目标方向形成“基础 → 专项 → 故障注入 → Capstone”的一条可走通路线：

| 方向 | 优先节点 |
|---|---|
| 后训练 | `PT-003/004/007/013` |
| VLM | `VLM-004/005/006/013/014` |
| Agent | `AGT-003/004/007/010` |
| 推理 | `INF-002/005` |
| 分布式 | `DST-001/003/008` |
| 通用手撕 | `ALG-003/005/007/009/011/015/016/017`、`TOK-003/004`、`NNL-006` |

当前 Algorithms 18 题、Tokenizer 4 题、GPU 8 题、CV 5 题全部 planned；“17 张手撕卡”还不等于普通求职者能真正动手练这些高频题。

### P1-2：打通知识卡到训练闭环

Knowledge detail 应展示 `related_problems` 的 title、ready/planned、前置锁定、环境需求和“开始练习”；对 planned 明确写“暂不可运行”。推荐最短闭环：

```text
岗位准备包 → 隐藏答案口述 → 追问 → 关联手撕题 → 公开测试 → 复盘
```

同时增加“我的岗位、八股/面经/手撕、P0/P1、阶段、可运行状态、今日 5 卡”筛选，并把入口放到 Home/Interview setup，而不只藏在 Learn 弹窗。

### P1-3：修正岗位准备包排序

`role-prep` 当前做 Track/Skill OR 过滤后保留 YAML 作者顺序直接 limit。实测后训练岗前 12 张前 10 张是 Transformer/Inference；Agent 岗前 12 张只有 1 张 Agent；Inference 岗只有 2 张 Inference。

建议按“主 Skill 命中数 → Skill weight → 主 Track → Blueprint round → P0/P1 → seniority → 可运行关联题”排序，并给每张卡显示“为何推荐”。

### P1-4：面试配置先做可用性预检

岗位/阶段/难度选项直接显示“可用、缺题、缺 PyTorch”徽标，默认选择首个可用难度。每轮至少显示候选数、是否重复上一场、缺失原因和降级方案。长期目标是常用 round 至少 3 个候选，而不是重复同一道题。

### P1-5：允许用户修改求职目标

桌面端目前无法修改目标岗位、真实 seniority 和能力自评；Onboarding 把 `new_grad + {}` 写入 Profile，Interview 的阶段只影响单场，不更新档案。

在 Career 或 Settings 增加“求职目标”：岗位、方向变体（含 VLM）、阶段、自评。明确说明历史成绩不变，只重新计算推荐路线和 readiness。

### P1-6：修复回访状态

- 已记录面试 Rubric 重开后应恢复 scores/evidence，只读展示或提供显式替换流程；不能显示“未评分但按钮禁用”。
- Learn 增加“已掌握/历史”筛选，可查看答卷、证据和下一次复测。
- 900×620 的 Exercise 首次进入默认展开题面，或在编辑器上方保留题目摘要和醒目的“阅读完整题面”。

### P1-7：统一 CLI 主路径并保证幂等

- README 首选 `llm-lab quickstart`，`init --track` 标成高级/兼容入口。
- 已有 Profile 再跑 quickstart 默认应 resume；变更岗位必须显式 `--reconfigure --role ...` 或交互确认。当前未传 role 会静默改成默认算法岗。
- README/`docs/interviews.md` 应使用与 GUI 一致的 `interview role-create/role-start/...`；旧 `interview create --track` 显式标 legacy/deprecated。
- `llm-lab --help`、`quickstart --help`、`interview --help` 补中文说明、示例、`roles list` / `tracks list` 和错误后的下一条命令。
- 修正 `docs/best-practices.md` 中不存在的 `--quest quest.python_data_reliability`；正确 ID 是 `python_data_reliability`，并将文档代码块纳入 smoke。

### P1-8：统一安装、依赖和平台承诺

- README.en 不应继续列 CI 不产出的 Windows 单文件 EXE；与 `docs/windows.md` 和 workflow 的 portable ZIP 保持一致。
- `requires-python` 与实际支持范围统一为 3.10–3.12，或让 doctor 对 3.13+ 明确报警。
- 环境可用性不要只用 `find_spec('torch')`；实际 import、DLL/ABI/CUDA 诊断应复用 `scripts/check_environment.py`。
- 增加 `doctor --desktop`、`--torch`、`--ai`，给出可复制修复命令。
- 明确源码安装必须 `git clone`；GitHub source archive 无 `.git` 时要么提供只读模式，要么在开始前给出准确说明。
- 自动 offscreen CI 不能替代 Explorer/Finder 双击、DPI、中文路径、SmartScreen/Gatekeeper 的原生 smoke。

### P1-9：优先翻译真实会遇到的内容

45 个 ready `task.md` 中仅约 4 个含中文；26 个固定 interview task/template/hints 中仅约 2 个含中文。先翻译 P0 岗位路线，保留英文术语对照；避免中文 Shell 中突然出现整页英文题面。

## 7. P2：体验与维护性优化

- Knowledge 来源提供标题、版本/发布日期、reviewed date、claim locator、“打开来源”和“复制链接”；离线仍可复制。
- Learn 卡片显示本地化 Skill title，内部 ontology ID 只放详情。
- 为知识卡增加独立 `unseen → learning → recall_due → recalled` 复习状态，但继续与 mastery 隔离。
- 提示按真实失败递进：预计用时、最小输入输出、shape/mask/gradient 检查表、失败测试诊断、迁移题。
- Onboarding 资源为空时提供“重新加载、运行 doctor、打开日志”，不要只留禁用 CTA。
- Rubric 使用中文维度名和 1/3/5 分行为锚点，提高自评一致性。
- 补键盘导航、焦点顺序、屏幕阅读器 `accessibleName`、对比度和字号缩放验收；合成截图不能替代可访问性测试。
- 建立 release constraints/build manifest，固定 Python、PySide6、pyside6-deploy/Nuitka 与平台 SDK；不要只依赖宽范围的在线解析。
- Home/Learn 的大面积空白优先用于“为何推荐、路径进度、下一步”和到期复测，而不是增加装饰性卡片。
- VLM 不应只作为算法岗 alias 的 optional quest；增加明确岗位变体或显式方向选择。

## 8. 建议的敏捷执行顺序

| 切片 | 目标 | 可验收结果 |
|---|---|---|
| A：发布真相 | 修 CI、Release 链接、版本/资产一致性 | `main` 全绿；所有下载入口有效；不再宣称不存在的版本 |
| B：首次 10 分钟 | 8 岗位都有第一题；ready 全可达；无 Torch 有清晰路径 | 新 Profile 从 Onboarding 到成功开始训练/面试无死路 |
| C：学习闭环 | Knowledge → 关联题 → 测试 → 复盘；历史可回看 | 从岗位准备到开始练习不超过 3 个主点击 |
| D：岗位纵向链路 | 后训练、VLM、Agent、Inference 各完成一条最小主线 | 每条至少含专项、故障注入、Capstone，不靠 planned 凑数 |
| E：原生发布 | Windows/macOS 真人首次使用与安装验证 | 双击启动、中文路径、依赖诊断、截图、SHA 与 Release 资产一致 |

每个切片独立提交、独立定向测试；不要同时重构 Application、Controller、QML、Catalog 和文档。跨 5 个以上核心文件时按 `AGENTS.md` 新建 ExecPlan。

## 9. 给本地 Codex 的接手动作

### 9.1 先安全同步

先检查自己的工作树，不要直接覆盖：

```bash
git status --short --branch
git fetch origin
git log --oneline --decorate -5 origin/main
```

如果工作树干净且本地没有独有提交：

```bash
git switch main
git pull --ff-only
git switch -c fix/alpha3-release-gates
```

如果本地有修改或独有提交，先在独立集成分支做 checkpoint，并额外保留备份引用：

```bash
git switch -c sync/main-handoff
git add <明确需要保存的文件>
git commit -m "checkpoint: preserve local work before main handoff"
git branch backup/before-main-handoff
git fetch origin
git merge --no-ff --no-commit origin/main
```

有冲突就逐文件处理；不确定时 `git merge --abort`。不要 `reset --hard`、不要 force push、不要把本报告列出的 106 个历史提交重新 cherry-pick 一遍。

### 9.2 第一项工作固定为发布门禁

建议首个分支只处理：

1. core collect 的 PySide6 可选依赖边界；
2. `LearnPage.qml` undefined → bool；
3. macOS symlink 稳定错误语义；
4. Alpha3 Release 链接真相。

先复现：

```bash
python -m pytest --collect-only -q
python -m pytest -q \
  tests/infrastructure/test_repository_contract.py \
  tests/infrastructure/test_knowledge.py \
  tests/infrastructure/test_application_service.py \
  tests/infrastructure/test_role_interviews.py \
  tests/infrastructure/test_windows_startup_hotfix.py
```

具备桌面依赖后再跑：

```bash
python -m pip install -e ".[desktop,ai,dev]"
python -m pytest -q \
  tests/infrastructure/test_desktop.py \
  tests/infrastructure/test_alpha3_truthful_ux.py \
  tests/infrastructure/test_onboarding_qml_hotfix.py
```

失败切片转绿后再运行一次完整 CI；不要为每个小修改重复全量回归。

### 9.3 必须继续保护的边界

- Catalog/DAG/Grader/Events 是事实源，AI 不能授予 mastery。
- 不读取或提交真实 `workspace/profiles/**`、材料、答案、Transcript、Secret、Oracle 或 Private Tests。
- 不为了让测试变绿而弱化路径穿越、symlink、答案锁定或证据边界。
- 对 planned 内容如实展示，不把知识卡数量包装成可运行题量。
- 先修 P0，再处理 P1；没有证据的 P2 不应阻塞敏捷发布。

## 10. 证据索引

| 结论 | 主要位置 |
|---|---|
| Agent 首次无任务 | `curriculum/roles/profiles.yaml`、`src/llm_interview_lab/catalog.py` |
| readiness 分母与上限 | `src/llm_interview_lab/application.py` 的 `dashboard()`、`curriculum/skills/ontology.yaml` |
| role-prep 排序 | `src/llm_interview_lab/application.py` 的 knowledge/role prep 逻辑 |
| ready 前置不可达 | `curriculum/catalog/structure.yaml`、`post_training.yaml`、`planned_systems.yaml` |
| 无 Torch 面试阻断 | `ApplicationService.interview_configuration()`、Role Blueprints、`InterviewPage.qml` |
| Knowledge 闭环缺失 | `desktop/qml/pages/LearnPage.qml` |
| 小窗口题面隐藏 | `desktop/qml/pages/ExercisePage.qml` |
| 阶段/自评不可编辑 | `OnboardingPage.qml`、`SettingsPage.qml`、Profile schema |
| Rubric 恢复失真 | `desktop/controller.py` 的 interview state、`InterviewPage.qml` |
| quickstart 覆盖岗位 | `src/llm_interview_lab/cli.py`、`ApplicationService.initialize_profile()` |
| 两套 Interview CLI | `README.md`、`docs/interviews.md`、`cli.py` |
| Alpha3 下载 404 | README 与平台文档、GitHub Releases/Tags |
| CI 失败 | `.github/workflows/ci.yml` 与 Actions run 33320073117 |

## 11. 最终判断

这个项目已经从“课程仓库”迈到了“可用的本地面试训练工作台”：产品边界、数据隐私、确定性掌握、模拟面试证据和研究型内容都很有辨识度。当前主要矛盾不再是缺功能，而是 **发布真相、首次可达性、岗位完成度和内容到练习的闭环**。

下一轮最优策略不是继续增加页面或堆更多 planned 节点，而是让一名普通用户能够：找到真实下载 → 选择任意岗位 → 立刻开始一项可运行训练 → 在没有 PyTorch/AI 时得到明确替代路径 → 完成一条岗位主线 → 回看证据与复测。做到这条闭环后，Alpha3 才有可信的发布基础。
