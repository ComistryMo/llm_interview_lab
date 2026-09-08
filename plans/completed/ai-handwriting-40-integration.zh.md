# AI 算法手撕 40 题资料内化

## 目标与验收

完整落地用户 2026-09-08 提供的《AI 算法手撕专项：面经来源与 40 道实现题》：40 项都有可追溯的 Catalog 入口、中文契约、可执行公开测试、提示和面试追问；17 篇面经保留证据范围，不冒充公司标准或独立样本统计。

## 当前事实

- 起点：`fix/dynamic-interview-full-flow-20260905`，`5cb4bb70066c2b88358d2fab4a5e6518073d51f4`；没有已有 tracked 改动。保留全部用户 untracked 文件及 UAT 数据。
- 用户在实施期间新增的未跟踪 `题目.md` 同样保留，不读取、不纳入本轮提交。
- 现有基础 MHA 接受预投影 Q/K/V；RoPE 接受预计算三角表；PT-002 接受已对齐 token；PT-015 是全 token 平均且没有参考 KL。不能把这些接口冒充附件的完整投影、位置偏移、shift 或逐回答归约。
- 现有大量主题是 planned。优先实现这些 ID；不同语义的进阶接口使用新 ID，不破坏旧题、Submission 和事件。
- 当前环境 PyTorch 2.13.0 CPU、NumPy 2.4.6。资料作者只运行过部分 NumPy 参考；本轮重新验证，不继承其通过声明。

## 范围 / 不做

实现课程内容、来源知识卡、岗位技能映射和已有动态面试的选题素材。不新增岗位、Provider、状态机、数据库或 UI 框架。不读取真实 Profile 或材料，不构建、不触发 CI、不发布。完整答案、私有验证保存在 ignored maintainer workspace，不提交公共仓库。

## 里程碑

1. [x] 完整读取资料，核对现有契约和来源边界。
2. [x] 补齐 40 项对应的练习资产与中文说明；新增 NumPy 环境的最小真实声明与检测。
3. [x] 将 40 项知识/追问及 17 篇证据纳入现有知识库，补齐技能和推荐路线；不将教学顺序全部变为硬前置。
4. [x] 逐个运行本轮 Oracle、公开及私有测试；验证 Catalog / 知识库 / 动态面试可选题范围。
5. [x] 复核来源、答案隔离和 Git diff，完成源码交付准备；提交与 push 的实际 SHA/结果在终局答复中核验，使用 skip ci，不合并 main 或发布。

## 验证

- 每个新增节点：`scripts/validate_oracle.py`，只验证本轮节点，成功后才能标记 oracle。
- 本轮定向集成：Catalog、NumPy 环境可用性、知识库引用、40 项覆盖及面试选题测试。
- `git diff --check`；不运行全量 pytest、跨平台打包或远端 CI。

## 风险与回退

不兼容的语义以进阶新节点承载，旧接口不变。新 ready 节点的所有硬前置必须已 ready。来源无法访问时标记“用户整理、原页未复核”；不猜年份、公司或样本数。若 Oracle 不通过，保持 contract 并继续修正，不伪标 oracle。

## 决策

- DEC-001：GRPO 逐回答均值与现有全 token 均值属于不同目标，分开练习并明确比较，不静默改 PT-015。
- DEC-002：保留 NumPy 题的手写梯度要求，不改成 autograd，也不把 NumPy 错标为标准库。仅增加实际依赖声明和现有环境检测分支。
- DEC-003：作者参考实现只进入私有验算；公开题面重新组织为任务契约，不附完整解法。面经只支持有限观察，不支持考频或录用概率。
- DEC-004：源码核对发现 Catalog 解锁依赖 mastered，而部分新旧相关题还没有独立已验证 D+2/D+7。对本轮新题，把这些推荐依赖降为题面推荐和 Quest 顺序，只以其可真正达成的基础祖先作为硬前置。新增测试通过真实 Catalog.unlocked 核实可达性；不改 Mastery 语义、不授予虚假掌握。
- DEC-005：真实候选测试发现算法岗遗漏了已有的 neural_layers、tokenization、generation 技能，且其 VLM Alias 没有 VLM track，导致七项对应题永远不能进入面试候选。为算法岗补齐这三个已有技能（沿用 secondary 级别权重）及 VLM track；不伪造题目的 Skill 标签、不新增岗位。准备度仍按当前技能覆盖重新计算，不产生新学习事件或自动授予掌握。

## 进度与复盘

实施完成。21 个 planned 节点落地、18 个进阶/缺口节点新增，复用 OPT-005 并补齐中文题面和检查点恢复测试；旧接口不被新公式替换。当前对应 23 个 PyTorch、14 个 NumPy 和 3 个标准库题。

知识库新增 40 张技术卡、17 张面经模式、70 条去重后的来源记录，现有来源按 URL 复用。每项技术卡有四个不同深度的追问。五条 Quest 覆盖全部 40 项；全部能通过现有已验证基础前置解锁，并在适用岗位/级别/依赖满足时成为动态面试候选。新增题没有完整英译，不把 English 导航冒充英文题面。

复核中处理的实际问题：

- INT8 公共用例原本错误要求浮点半舍入边界在缩放后整数结果逐位一致；改用不落在半边界的比例不变量，同时保留独立 ties-to-even 测试。
- PPO/GRPO 忽略 token 的巨大有限 log-ratio 不应参与指数并污染梯度；增加公开反例并修正本轮私有参考，再分别重跑对应 Oracle。GRPO beta=0 跳过 reference KL 项。
- MHA 增加全屏蔽行反向传播测试，要求有限零梯度。
- OPT-005 旧 5 秒验算预算在本机出现私有参考超时，调整为本批次的 20 秒上限后公开 8 / 私有 2 全部通过；不据此宣称算法性能提升。
- 文档/公开题面补全多函数和类方法签名，防止只展示第一个接口。

### 实际验证（2026-09-08）

- 通过既有 `scripts.validate_oracle` 的 `_run` / 真正 Grader 验证本轮 39 个节点；`scripts/validate_oracle.py OPT-005` 验证复用题。40 项最终均 passed，合计公开 **226 passed**、私有 **63 passed**；逐题原始结果在 ignored `workspace/maintainer/ai40-integration/validation-results.json` 及维护者 Oracle reports，不公开参考实现。
- `tests/infrastructure/test_knowledge.py` 8 项通过，包括真实 CLI `knowledge validate --with-catalog` 与 ApplicationService 入口。
- 最终合并范围测试：`test_ai_handwriting_collection.py`、`test_roles.py`、`test_lean_v2_catalog.py`，加上现有动态 Session 单轮创建、环境提示和知识库 CLI 三个指定测试：**33 passed, 1 skipped（35.83s）**。
- 跳过项：Windows 没有创建 symlink 的权限；不绕过机器权限去伪造通过。
- 新集合检查覆盖 40 项映射、四个公开资产、中文题面、Python 3.10 语法、独立追问、来源分组、NumPy 缺失/存在、实际候选范围、可达解锁、推荐路线、旧接口保留、真实 ContextBuilder 携带岗位技能但不预生成题单，以及文档本地链接。
- `git diff --check` 通过。没有运行全量 pytest、RC CI、桌面构建、GPU 验证或真实外部 AI 会话；没有触碰真实 Profile、材料、录音或 API Key。

### 剩余边界

新增题只有手动 D+2/D+7 迁移方向，没有独立已验证复测包，不能被宣称 mastered。模拟面试选题和上下文连接已经自动化验证，但新提示对真实模型的追问质量仍待人工观察。多数社区原页未独立全文复核，统一保留 anecdotal / unverified 与来源作者分组，不作公司标准或考频推断。没有把四十项教学实现包装成完整训练/Serving 系统。


## 40 项落地对照

详见 [正式内容入口](../../docs/content/ai-handwriting-40.zh.md)。

- AI01 → PT-003 / COD-AI-001：已规划节点落地
- AI02 → ATT-019 / COD-AI-002：新增进阶/缺口节点
- AI03 → ATT-020 / COD-AI-003：新增进阶/缺口节点
- AI04 → ATT-021 / COD-AI-004：新增进阶/缺口节点
- AI05 → NNL-006 / COD-AI-005：已规划节点落地
- AI06 → INF-013 / COD-AI-006：已规划节点落地
- AI07 → ATT-011 / COD-AI-007：已规划节点落地
- AI08 → PT-022 / COD-AI-008：新增进阶/缺口节点
- AI09 → PT-023 / COD-AI-009：新增进阶/缺口节点
- AI10 → LOSS-004 / COD-AI-010：已规划节点落地
- AI11 → LOSS-006 / COD-AI-011：已规划节点落地
- AI12 → PT-024 / COD-AI-012：新增进阶/缺口节点
- AI13 → TML-004 / COD-AI-013：已规划节点落地
- AI14 → LOSS-010 / COD-AI-014：已规划节点落地
- AI15 → TNS-014 / COD-AI-015：已规划节点落地
- AI16 → ATT-015 / COD-AI-016：已规划节点落地
- AI17 → NNL-014 / COD-AI-017：已规划节点落地
- AI18 → NNL-005 / COD-AI-018：已规划节点落地
- AI19 → TOK-001 / COD-AI-019：已规划节点落地
- AI20 → OPT-005 / COD-AI-020：复用并深化
- AI21 → LOSS-016 / COD-AI-021：新增进阶/缺口节点
- AI22 → TML-006 / COD-AI-022：新增进阶/缺口节点
- AI23 → TML-001 / COD-AI-023：已规划节点落地
- AI24 → NNL-016 / COD-AI-024：新增进阶/缺口节点
- AI25 → NNL-009 / COD-AI-025：已规划节点落地
- AI26 → CV-002 / COD-AI-026：已规划节点落地
- AI27 → TML-007 / COD-AI-027：新增进阶/缺口节点
- AI28 → TML-008 / COD-AI-028：新增进阶/缺口节点
- AI29 → ATT-022 / COD-AI-029：新增进阶/缺口节点
- AI30 → PT-009 / COD-AI-030：已规划节点落地
- AI31 → PT-010 / COD-AI-031：已规划节点落地
- AI32 → NNL-017 / COD-AI-032：新增进阶/缺口节点
- AI33 → INF-008 / COD-AI-033：已规划节点落地
- AI34 → REC-007 / COD-AI-034：新增进阶/缺口节点
- AI35 → REC-008 / COD-AI-035：新增进阶/缺口节点
- AI36 → ATT-008 / COD-AI-036：已规划节点落地
- AI37 → TML-009 / COD-AI-037：新增进阶/缺口节点
- AI38 → REC-009 / COD-AI-038：新增进阶/缺口节点
- AI39 → VLM-001 / COD-AI-039：已规划节点落地
- AI40 → TNS-017 / COD-AI-040：新增进阶/缺口节点
