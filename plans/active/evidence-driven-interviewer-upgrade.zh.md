# 证据驱动面试官升级工程记录

## 当前状态摘要（2026-09-10，有限收尾核对）

**SLICE3_LOCAL_ACCEPTANCE_PASSED / REAL_MODEL_QUALITY_UNRUN**。当前续接以文末“切片三有限收尾核对”为准；中间所有 `SLICE3_PENDING`、“未实施”和“进行中”均是保留的历史断点，不代表当前仍需重新实施切片三。历史失败记录不删除。

本轮只补测两个中断窗口，实际发现并最小修复：① 答辩关闭但 GUI finish 未执行时，重启仍为 active；② Codex 主动结束只发 interrupt，未建立现有停止确认 fence。新增三例先 **3 failed**，修复后 **3 passed**；共享路径 **4 passed**，证据映射见文末。不扩展结构，不改变模型、时间或权重。真实模型质量、真实延迟与专家盲审始终 **UNRUN**。

## 目标、依据与边界

唯一任务书：根目录 `codex_interviewer_structural_upgrade_prompt.zh.md`。本记录承接而不覆盖历史计划。顺序执行，不使用子 Agent；不提交、推送、打包、全量回归或真实模型调用。不读取真实 Profile、材料或密钥。

核实基线：`main` / `b954c71d6a7029010fc247cbf7eef6c880a102f1`。开始时没有已跟踪文件改动；任务书、私人反馈、UAT 目录等原有未跟踪内容全部保留。

## 已读事实与调用链

- 已完整阅读任务书、根 AGENTS.md、PLANS.md、统一难度工作台与自适应深度历史计划。
- 起始基线的新会话为 interaction_version=2；当前工作树默认协议 3。旧版 `flow_coverage` 的 `coverage.sufficient` 不能作为证据闭环。
- 正式调用链：InterviewPage → Controller 提交/锁定回答 → Context Builder → Provider 或 Codex → `advance_dynamic_role_interview` → 原子保存 Session → 正式页面刷新。
- 现有延后评分、等待时间、取消和异步身份隔离继续复用，不重写 Controller。

## 范围与连续里程碑

1. **切片一（有限验收已补齐）**：协议 3、状态/引文/版本冲突校验、单轮事务、状态驱动转场、两类传输接线及安全缓冲；版本 1/2 恢复兼容。原始 V2 快照保留。晚到、重复、重启、损坏和写入失败验收见本轮续接记录。
2. **切片二（生产接线及本地验收完成）**：五个方法包、八个专家主题、缺口检索与上下文预算；48 场景编译/输出回放入口。真实模型语义质量 UNRUN。
3. **切片三（已接入，最终增量核对见文末）**：代码答辩、父题汇总评分、正式 Provider/Codex Fake 整链及时间/故障验收。原五条轨迹保留，第六条已接线；真实模型语义质量仍 UNRUN。

## 验证计划

使用隔离合成档案、Fake Provider/Codex；检查真实业务入口、引用伪造、事务失败不写入、重试/重启/过期结果、稳定标识与转场。旧协议保留专门回归；不以 Mock 通过冒充真实模型质量。真实传输与 macOS 实机验证未授权/未执行。

## 风险、停点与决策

- 本地引文校验只证明原话存在，不证明技术正确；模型支持与确定性验证明确区分。
- 协议 3 与版本 2 显式分派；共享计时/评分分支只列举已知版本，不使用 `>= 2`。
- 无效依赖更新整轮拒绝，保留锁定回答、原位重试；不自动付费重试或降模型/推理强度。
- 问题通过状态事务校验后才展示；不泄露 JSON、推理或参考材料。

## 实际进度、测试与续接

- 2026-09-10：新增 `interviewer_state.py`，落盘经历、主张、证据、缺口、矛盾、追问和关闭原因。引文保存回答 SHA、连续原文与本地计算的起止位置；模型判断来源和短依据单独保存，不把原文匹配等同答对。
- `role_interviews.create_dynamic_role_interview` / ApplicationService 默认新建协议 3；显式版本 2 用于恢复契约回归。历史会话不迁移、不重写指纹。协议 3 禁止单独追加题目或活动阶段提前评分。
- `advance_dynamic_role_interview` 校验请求启动时的 Profile/Session/Question/回答 SHA/状态 revision/timeline，合并状态副本后判断转场，再一次原子保存状态与新问题。失败保留锁定回答，重试不重复记账。
- `context_builder.build_role_interview_context_preview` 提供同一个证据协议、状态快照、实际岗位与已加载知识范围；Provider 和 Codex 共用解码与响应 Schema。普通模型配置及 Codex 线程复用保留。
- Controller 捕获请求快照，完成时重新核对当前授权与状态；协议 3 不再提前展示 JSON 中的 follow_up，无论字段顺序如何。旧版流式展示保持原行为。原位重试、中文输入、下一问历史、取消与等待计时使用原入口。
- `interview_flow` 区分讨论主题与模型支持的覆盖。同一主张可通过实际回答证据在经历/原理两阶段取证，不复制成两个主张。未知关闭不计作能力支持，时间转场保留未解决缺口。
- CLI 的协议 3 当前题上下文不再推荐活动阶段 role-score；已有应用内结束后逐题评分和报告入口保留。
- 未修改 Provider 实现、模型名、推理强度、用户数据、语音、Practice 或 Mastery。

### 实际验证记录

全部使用临时合成 Profile；QML 测试加载正式 Main.qml，只有网络传输替换为 Fake。无真实模型请求。

1. 修改产品代码前，`LLM_LAB_CAPTURE_V2_BASELINE=1` 下运行 `test_interviewer_evidence.py`：**1 passed**。完整编译上下文保存为 `tests/fixtures/interviewer-v2-baseline.json`，记录真实起始 SHA。后续只规范化随机合成档案名称进行对比，没有覆盖旧快照。
2. 首轮旧协议问题优先回归：`test_question_first_interview.py` **20 passed**；同期基线测试因随机档案名差异失败，修正测试变量后通过，不曾重录基线掩盖差异。
3. 最后一组主体定向命令：

```text
.venv\Scripts\python.exe -m pytest tests/infrastructure/test_interviewer_evidence.py tests/infrastructure/test_evidence_interview_desktop.py tests/infrastructure/test_question_first_desktop.py::test_one_submit_streams_next_and_finish_grades_once tests/infrastructure/test_question_first_desktop.py::test_codex_reuses_transport_for_question_then_end_grading tests/infrastructure/test_dynamic_interview_flow.py::test_context_keeps_resume_jd_and_prior_answers_not_future_questions tests/infrastructure/test_dynamic_interview_flow.py::test_invalid_ai_stage_does_not_commit_score_or_extra_question -q -s
27 passed in 87.89s
```

覆盖：合法证据事务、改数字/拼接/跨题假引文、过期 revision、跨 Profile 请求、未知方法/知识/主张、越级转场、暂停恢复、去重与 GRPO advantage/ratio/reduction 分离、本轮补齐证据后转场、未知后相邻追问及关闭、时间转场、未消歧不能重标支持、原子写入失败、结束评分去重和脱敏异常。

4. 后续补充 CLI 定向测试 **1 passed in 3.70s**；对应结束评分测试再次 **1 passed**。CLI 测试初次缺少隔离仓库 AGENTS.md，补充公开策略 fixture 后通过。
5. 正式 QML + Mock Provider：故意返回不存在的引文 → 留在 q-001 → 点击真实“重试”按钮 → q-002；期间不展示未校验正文，成功后历史保留、中文输入法组字隐藏提示、提交中文正常。Fake Codex 两轮调用复用同一个线程，输入/响应协议与 Provider 一致；取消不丢回答。
6. Mock Provider 完成响应后，本地重新校验上下文、保存并刷新页面的测量值 **179.06 ms**（前一次 181.82 ms）。这不是远端模型首字/整轮耗时，也不是性能保证。未测真实模型延迟。
7. `git diff --check` 通过（Git 提示 QML 的 LF/CRLF 转换策略，不是差异空白错误）。

测试过程中还修正了测试使用不存在的取消方法，以及 Mock 从旧授权标记读取上下文的问题；最终调用实际 stopInterviewGeneration 和捕获的传输内容。没有为测试放宽生产校验。

### 首轮历史停点（本轮进展以下方续接记录为准）

- **不能宣称整个任务已完成。** 切片二和三未开始；当前只启用 always-on 策略对应的 `core` 方法，不宣称已有五个方法包或专家知识审查。
- 继续切片一验收：补充更多状态损坏/实际并发晚到、显式用户跳过阶段的授权接线与覆盖报告深度一致性案例。当前模型不能代替用户跳过；已有“结束本场”保留，没有新造自动跳过操作。
- 然后切片二：在 `interviewer_state.response_schema/instruction`、Context Builder 和同一传输 Schema 上接入最多两个 allowlist 方法；深化八张现有卡、按缺口检索、限制历史与证据上下文预算。当前仍沿用现有知识候选和完整历史上下文，不能声称长面试 token 预算已经优化。
- 然后切片三：在 Controller 的 coding 提交后直接 finish 分支接入答辩子阶段，保持原题与代码冻结、计时和原权重；补齐 48 案例及至少 6 条多轮轨迹。目前代码提交仍沿用既有结束后评分，**没有代码答辩**。
- 真实 Codex/DeepSeek 验证、盲审专业问题质量、完整场次性能和 macOS 实机验证均 **UNRUN**。既有模型“只返回思考”问题不因本轮结构升级宣称解决。
- 当前 HEAD 仍是上述基线；全部改动留在工作树。未提交、未推送、未构建/发布、未运行全量回归。原有未跟踪私人内容全部保留。

## 阶段复盘

### 2026-09-10 续接初始记录（历史）

- 恢复时重新核对证据原文、回答 SHA、已处理轮次、追问和矛盾对象关联；复用规范回答路径，不静默清空或新建。
- Provider 取消立即释放本次操作的等待门控；旧 Worker 仍只能释放自己的 token。可控 Fake transport 先让 B 完成、再放行 A，重复 B 结果不增加题目；旧 A 失败不清除 B 等待。
- 首组 `test_interviewer_evidence.py test_evidence_interview_desktop.py`：31 passed / 1 failed，174.59s。失败为测试直接读取可选 ai_error 字段；改为 get 后单独重跑晚到测试：1 passed / 14.63s。没有放宽产品校验。
- 报告新增逐 criterion 状态/关闭原因，困难深度与未解决缺口影响覆盖完成度。未知/时间暂缓不计能力支持。补充矛盾换名绕过与写入失败后重试测试，待本轮下一次定向运行。
- 五个方法资源已开始编写，尚未接入请求，不能宣称切片二完成。下一步 GRPO 真实知识卡→确定性检索/方法加载→编译请求→脚本响应事务。

状态：`SLICE1_IMPLEMENTED_TARGETED_TESTS_PASSED / STRUCTURAL_UPGRADE_INCOMPLETE`。

可继续从现有协议 3 与上述测试推进，不回退、不重新实现、不重录历史基线。定向测试证明了本地状态闭环与正式传输接线，不证明模型已达到专业面试官的语义判断水平。

## 2026-09-10 本轮实施与验收

### 1. 切片一的有限收尾

- `role_interviews.load_role_interview` 恢复时调用 `interviewer_state.validate_saved_sources`，重新核对原始回答 SHA、连续引文起止、主张/缺口/矛盾关联、已处理回答与追问 revision。坏 hash、假引文、缺失主张、缺失回答、未知状态版本、错误 criterion 均拒绝恢复，不清空、不新建、不标支持。缺失锁定回答使用具体恢复错误。
- 正式 Controller + 事件控制 Fake Provider：取消 A 后同一锁定回答发起 B；A 的失败回调不清 B 等待，B 成功后 A 晚到及 B 重复完成均不再落盘。取消只释放本次 Worker 的 busy token，不释放其他异步任务。
- Fake Codex：取消后遵循原有 interrupt 确认再发 B，A 的晚到正文/完成和 B 重复完成不污染页面。复用线程、模型与推理强度不变。
- 写入失败先拒绝整轮；正式 QML 重试按钮可恢复同一回答并只追加一次下一问，revision 从 0 到 1，无半轮状态。中文组字与历史显示沿用正式页面测试。
- 覆盖报告增加逐 criterion 状态、缺口与关闭原因。讨论过与支持分开；未知、时间暂缓不算支持；困难深度仍要求机制/实现/验证或边界。未消歧矛盾不能用改名或新增经历下同一考点的“支持”绕过。时间转场保留证据缺口。
- 未新增跳过 UI。模型单独输出 `user_skip` 不能授权转场；已有结束入口保持。没有需要阻塞切片二的有限验收缺口。任意自然语言同义主张的语义等价判定不是本地校验能够保证的能力。

### 2. 方法实际加载链与边界

`build_role_interview_context_preview` → `interview_expertise.retrieve` → `route_methods` → `load_methods` → `bounded_parts` → Provider/Codex 正式请求 → 原有 `advance_dynamic_role_interview` 状态事务。

五个目录均为 `coach/skills/<id>/SKILL.md`：

- `mechanism-implementation-probe`
- `experiment-causality-audit`
- `counterexample-constraint-transfer`
- `ownership-consistency-check`
- `code-defense-failure-analysis`

按 skill-creator 约束编写必要的适用/禁用条件、输入、动作、空泛识别、停止、禁止行为和好坏对照；五个文件均通过格式校验。没有增加通用 Skills 平台、RPC、外部安装或工具权限。

固定白名单、精确目录、版本 1 和内容 SHA-256；实际请求和落盘 turn_decisions 记录加载的版本/hash。core 常驻，每轮最多两个专业方法。阶段、当前回答信号、未解决缺口/矛盾、岗位允许的知识范围和困难约束共同参与选择；词项只用于工具路由，不是正确性裁决。Schema 和事务只允许本轮实际加载的方法，未加载但名称合法的方法也拒绝。

`code-defense-failure-analysis` 当前仅用于候选人口述的具体实现/失败；**尚未实现锁定代码后的答辩子阶段**。

### 3. 八个主题与实际依据

复用 `curriculum/interviews/knowledge.yaml` 的原卡，在现有 schema 增加可选 `expert_reference`，由原 `knowledge.py` loader 的 `raw` 承载，不复制第二套完整答案库。

| 主题 / 卡 ID（topic_id） | 本轮 criterion | 固定依据 |
|---|---|---|
| GRPO / EGT-QB-028 | advantage、reference、ratio、reduction、validation | DeepSeekMath 2402.03300v3 §4.1 |
| DPO / EGT-QB-026 | mechanism、reference、reduction | DPO 2305.18290v2 |
| KL / EGT-QB-030 | reference、numerics、reduction | DeepSeekMath 2402.03300v3、DPO 2305.18290v2 |
| SFT mask / EGT-QB-014 | mask、shift、packing | PyTorch v2.5.1 CrossEntropyLoss 源码 |
| Attention / EGT-QB-048 | scaling、mask、numerics | Attention Is All You Need 1706.03762v7 |
| GQA / EGT-QB-058 | implementation、cache、validation | GQA 2305.13245v3 |
| KV cache / EGT-QB-011 | cache、implementation、validation | Transformers v4.46.0 KV cache 文档 |
| Adam/AdamW / EGT-QB-001 | decay、implementation、validation | Decoupled Weight Decay 1711.05101v3 |

每张卡的 `expert_reference.source_pins` 保存精确链接，原 `source_claims/source_ids` 保留；每个 criterion 有 mechanism、variants、misconceptions、discriminator、adjacent、stop，另有适用假设。GRPO 的 std 约定、reference/old 策略、长度归约、奖励与独立评测不合并成一个掌握状态。

检索顺序：本轮相关开放缺口 → 新机制 → 当前主题未验证 criterion → 岗位词项召回；已关闭考点降权，同主题其他 criterion 可进入。最多三个精简参考。当前问题主题用于同优先级排序，防止回答提及 KL/Attention 就把正在考察的 GRPO/GQA 全部挤出。追问历史以 topic/criterion/claim/action 给模型作重复控制，关闭考点的重复取证另有本地拒绝；不声称能确定性识别所有同义问题。

### 4. 三个实际编译请求

来源为隔离运行器的 `s001/s002/s003.request.json`，不是手写提示词示意。下面的“充分/空泛/错误”是评测侧标签，**未发送给面试官**。

| 输入类型 | 实际方法 | 实际参考 criterion |
|---|---|---|
| 正确充分：组标准化计算并指出 KL 不一定无梯度 | mechanism-implementation-probe + counterexample-constraint-transfer | GRPO advantage、validation；KL numerics |
| 空泛：术语与效果宣称，缺计算细节 | experiment-causality-audit + mechanism-implementation-probe | GRPO advantage、ratio、reduction |
| 具体技术问题：把零方差优势设为正一 | mechanism-implementation-probe + counterexample-constraint-transfer | GRPO advantage、ratio、validation |

48 场景的公共启动历史仅记 `claim-0001/contribution/open`，允许该已加载主张与本轮从回答新建的合法主张；不会提前从评测标签填“答错/掌握”。另有 GRPO 六类闭环测试先通过真实事务建立 `claim-0001/EGT-QB-028/advantage` 缺口：构建器据此优先加载该点；脚本响应分别记录 partial/disputed/explicit_unknown/model_supported，充分情形认可优势并新建 ratio 缺口，矛盾情形引用两处实际回答。**这些下一问及判断来自 Fake 脚本，不是模型自动识别错误的证据。**

### 5. 传输等价、源范围与预算

- 同一锁定合成回答：实际 Provider 入口 1 次 Fake 请求后保留失败回答，再通过现有公开 Codex 发送入口发 2 次（含取消重试），捕获并比较业务上下文和指令；只规范化自然流逝的剩余秒数，业务内容等价。不是允许用户 UI 任意更换已冻结面试官。另有 Codex 正常两轮复用同一线程的测试。两类传输使用同一个协议与本轮 method enum；均无真实网络请求。
- 上限为最终本轮载荷 **64,000 Unicode 字符 / 160,000 UTF-8 字节**，不是 token。正文装配为指令/schema 留 14,000 字符与 42,000 字节余量；近两轮历史软预算 14,000 字符。最终 Provider messages、Codex prompt + output_schema 都重新测量。
- 保留当前完整题目/回答、授权材料、目标主张与矛盾两侧原文、少量专家依据；先省略旧完整历史，再剔除最近历史的较早轮，最后可选旧式知识召回。必需内容仍超限时明确报错且不发送，不截断当前回答或整段 JSON。
- 完整原始问答仍本地保存。发送范围记录 question_id、回答 SHA 和原始起止位置；旧索引不是证据。即使本地存在旧原话，只要本轮未发送该范围，事务也拒绝模型引文。允许追问目标同样限制于已加载对象或本轮新主张。
- 最新长合成测试：8 条早期长回答，省略 6 条完整历史，实际业务正文 **41,366 字符 / 83,213 UTF-8 字节**；当前回答完整、必要旧证据片段保留，省略尾部引用被拒绝，超额必需内容也被拒绝。此数字是构建器业务正文，不是 token、HTTP 全包或真实模型延迟。
- Codex 线程仍复用；本轮新增文本受控不代表累计线程上下文受控，当前不能观测或保证整个线程总预算。既有 UI token 估算提示不作为预算计量事实。不泄露参考内容到候选人正文、普通错误日志或诊断导出。

### 6. 48 场景、旧基线与运行入口

```powershell
# 默认仅编译正式请求、校验路由/来源/预算/schema/评测隔离；不请求模型。
.venv\Scripts\python.exe -X utf8 scripts/evaluate_interviewer_expertise.py
# 对同一组输入，从记录原始提交导出公开源码到隔离目录并编译旧版请求。
.venv\Scripts\python.exe -X utf8 scripts/evaluate_interviewer_expertise.py --export-baseline
# 可选 --responses <目录> 读取明确提供的 sNNN.txt 输出，按对应协议解析及事务回放。
```

数据为 `tests/fixtures/interviewer-expertise-scenarios.json` 与同名 `.schema.json`：八主题 × 六类回答；`input` 与 `evaluation` 分离。同主题问题保持一致，矛盾例含两处真实历史，充分例允许认可。生产构建器只收到 input，不接收 answer_type、gold、case 名称或评测结论；运行器只在编译完成后检查 sidecar。

输出有实际 request、仅审核使用的 sidecar、输入与编译 hash、方法/知识版本、校验结果、字符/字节度量。可保存真实输出文件供未来审核，但本轮仅用脚本响应验证回放接口。所有 semantic_quality、real_latency、expert_blind_review 维持 UNRUN，不从 Fake 计算准确率。

原 V2 快照不足以还原全部 48 场景，故从 `b954c71d6a7029010fc247cbf7eef6c880a102f1` 使用 `git archive` 只导出公开源码及资源，写每文件 hash 清单并设置只读，用独立 Python 进程优先加载原提交代码。没有 checkout/reset 当前树，没有重录快照，也没有把新构建器 version=2 当旧策略。旧输出按旧 coverage 契约解析，新输出按协议 3 解析。

原始源码导出：`C:\Users\ComistryMo\AppData\Local\Temp\interviewer-eval-14d1mmcq\baseline-source`。旧版 48 场景成功产物：`C:\Users\ComistryMo\AppData\Local\Temp\interviewer-eval-9luj7_n4`。最终新版结果及比较见下方完成记录。

另有六条多轮设计 `interviewer-expertise-trajectories.json`；五条非答辩轨迹每条四轮，走真实状态事务（认可后转新考点、未知相邻追问、矛盾消歧、时间转场、重启/坏引用重试），**5 passed / 84.52s**。第六条 `coding_defence` 明确 pending_slice3。

### 7. 实际测试、失败与修正

主体定向命令（不是全量 pytest）：

```text
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interviewer_evidence.py tests/infrastructure/test_interview_expertise.py tests/infrastructure/test_evidence_trajectories.py tests/infrastructure/test_evidence_interview_desktop.py tests/infrastructure/test_question_first_interview.py -q --disable-warnings --maxfail=2
69 passed in 538.58s
```

后续增量（与上面有覆盖重叠，不相加冒充独立案例数）：

- 方法路由 + evidence 中 allowlist/corrupt/invalid_decision 定向：**17 passed, 14 deselected / 117.80s**。
- 响应产物回放 + 正式 QML `test_provider_buffer_rejection_retry_and_visible_history` 的坏引文/写入失败两种情形：**3 passed / 48.03s**。
- 最新预算与 GQA 排序补测：最初 **1 failed, 1 passed / 36.93s**；长会话通过，GQA 测试错误使用后训练岗位而非该场景的算法岗位。改回合成场景的真实角色后，排序回归 **1 passed / 7.15s**。没有扩大产品岗位选题权限。
- 早期 GRPO 六类接线 **6 passed / 46.19s**；后续 GRPO + V2 快照 + 桌面接线 **11 passed / 87.60s**。
- 旧评测第一次失败为 fixture 使用不存在的 role_id，替换为仓库真实角色；只读基线第一次失败为 Windows TEMP 短路径/绝对路径比较，统一 resolve 后成功，没有覆盖 hash。回放测试曾缺公开 AGENTS fixture，改为只复制公开 allowlist 后通过。
- 48 场景检查实际发现 GRPO/KL、GQA/Attention 相邻主题挤出当前主题，补充当前问题机制及同优先级主题锚点排序；不是删除断言以获得通过。

### 8. 修改清单与后续边界

本轮实改：`interviewer_state.py`、`role_interviews.py`、`interview_flow.py`、`ai/context_builder.py`、`desktop/controller.py`；新增 `interview_expertise.py`、`ai/interview_context_budget.py`；现有 `knowledge.yaml` 及 schema；五个上述 SKILL.md；`scripts/evaluate_interviewer_expertise.py`；三个 expertise 场景/schema/轨迹 JSON；新增或续写 `test_interviewer_evidence.py`、`test_evidence_interview_desktop.py`、`test_interview_expertise.py`、`test_evidence_trajectories.py`；本工程记录。

保留此前已有 ApplicationService/context/InterviewPage、会话 schema、dynamic/input/unified 测试和 V2 快照改动；本轮未再改 QML。用户原有未跟踪反馈、任务书、UAT、图标等不删除、不读取内容、不纳入任何提交。

四种状态严格区分：**方法/专家资源已编写；已进入正式 Provider/Codex 请求；本地定向测试通过；真实模型语义质量未验证**。没有保证模型判断全部正确，没有把 Fake 追问描述为质量提升，也没有修改既有“只返回思考”的底层传输故障。

精确续接：切片三应从 `AppController.submitInterviewAnswer` 当前 coding 锁定后直接 finish 的分支进入，复用同一问题/代码冻结、证据事务、计时与原权重，接入答辩子阶段后再执行第六条轨迹；本轮不做临时跳过、不新造答辩页。真实模型传输、专业盲审、整场真实延迟和 macOS 实机验证仍 UNRUN，未经新授权不执行。

HEAD 保持原基线，修改均留工作树；无提交、推送、打包、发布、全量回归、真实模型调用或真实 Profile/材料/密钥读取。

### 9. 本轮最终核对结果

最新运行 `.venv\Scripts\python.exe -X utf8 scripts/evaluate_interviewer_expertise.py`：**48/48 编译校验通过**，输出 `C:\Users\ComistryMo\AppData\Local\Temp\interviewer-eval-pqvujo16`。与上述原提交旧版结果逐场比较：48 个 `id/input_sha256` 全部一致；不是只比较场景数量。两组 `network_calls=0`。

| 口径 | 最小字符 | 最大字符 | 最小 UTF-8 字节 | 最大 UTF-8 字节 |
|---|---:|---:|---:|---:|
| 新版业务对象（system + instruction 的 JSON） | 26,752 | 31,664 | 42,472 | 48,370 |
| 原提交旧版同类业务对象 | 18,974 | 25,462 | 33,944 | 43,415 |

新版最终 Provider messages 最大 31,699 字符 / 48,405 字节；Codex prompt + output_schema 最大 37,582 字符 / 54,288 字节。短场景增加专业依据后比旧版大；不宣称总是更省 token、更快或质量提升。长会话控制的收益是避免无限追加完整历史，仍受前述 Codex 累计线程限制。

最后增量命令可复现为：

```text
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interview_expertise.py::test_method_allowlist_and_latest_answer_change_route tests/infrastructure/test_interviewer_evidence.py -k "allowlist or corrupt or invalid_decision" -q --disable-warnings
# 17 passed, 14 deselected
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interview_expertise.py::test_offline_response_artifact_replay_uses_production_transaction tests/infrastructure/test_evidence_interview_desktop.py::test_provider_buffer_rejection_retry_and_visible_history -q --disable-warnings --maxfail=1
# 3 passed
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interview_expertise.py::test_gap_priority_keeps_current_criterion_despite_adjacent_topic -q --disable-warnings
# 最后修正合成角色后 1 passed
```

最终 `git diff --check` 通过。仅有继承 QML 文件的 LF→CRLF 策略提示，无空白差异错误。分支 main，HEAD `b954c71d6a7029010fc247cbf7eef6c880a102f1` 未变。

当前裁决：`SLICE1_FINITE_ACCEPTANCE_PASSED / SLICE2_LOCAL_ACCEPTANCE_PASSED / REAL_MODEL_QUALITY_UNRUN / SLICE3_PENDING`。

本轮停止于上述范围。切片二的资源、生产编译请求、事务与离线验收均已接线；代码答辩不在本轮实现，真实模型质量仍待另行授权验证。

## 2026-09-10 切片三续接（进行中，以下为实际进度）

重新核实 main / b954c71d6a7029010fc247cbf7eef6c880a102f1 及现有未提交改动，保留前两切片实现。顺序执行，无子 Agent、真实模型、真实档案/材料/密钥读取、额外代码执行、提交或构建。

- 实际接入断点为 `AppController.submitInterviewAnswer` 的 coding 直接结束分支，`submitInterviewCode` 继续复用锁定入口。新增 `coding_defence.py` 处理 coding 内部子题；口头子题 kind=oral，不重新锁定父题代码。
- 新建接口冻结可选 `coding_defence_version=1`，只在新建且明确启用时写入及纳入指纹；无标记的历史协议 3、协议 1/2 保留旧行为，恢复不补字段。ApplicationService 与底层 create_dynamic_role_interview 同步接线。
- `coding_defence.sources/advance/validate` 使用 canonical 锁定快照、代码 SHA、版本关联运行结果及独立口头回答，复用 interviewer_state 引文/快照/事务/恢复校验。首问必须引用锁定代码，第二问必须仍有具体缺口；第二答只保存、关闭和启动既有父题评分，不再请求下一问。
- 统一 60 秒剩余时间门槛（为阅读和口头回答留最小窗口），使用现有候选时间，不新增计时器。少于门槛或无可引用代码记录原因后结束；失败保留 pending 与原回答，不冒充跳过。
- Context Builder、专业方法、来源范围和最终传输预算已接入；实际加载 code-defense-failure-analysis。现有 coding_review 先核对冻结题面版本，不匹配就不加载。父题的统一评分包含锁定代码/执行事实/所有答辩，不给子题增加权重。
- 正式 InterviewPage 只增加父题只读代码查看，沿用文本/语音、重试与报告。旧版本运行结果增加显式版本提示，避免把旧代码通过当作当前通过。
- 新测试 `test_coding_defence.py` 首组 **7 passed / 237.88s**：一问、两问、恢复/假引文/写入失败重试、59/60/61 秒边界、历史标记。两种正常路径父题评分权重不变，代码 hash 不变；这均是脚本事务测试，执行次数 0，不代表代码逻辑正确。
- 正式 QML + Fake Provider 整链已通过；同组 Fake Codex 曾在回调投递时序等待失败，正在以精确 turn ID 修正测试并复验。不得提前宣称 Codex 整链通过。
- 48 场景正在写入持久忽略路径 `workspace/maintainer/evidence-driven-interviewer/slice3-48`。新增显式评测传输函数 `transmit_authorized_case`，复用调用方传入的已有 Provider/Codex adapter、逐载荷确认 hash；默认只编译、不查询密钥、不联网。离线回放本身仍不等于真实传输。

当前精确续接：完成 Codex Fake 整链时序核查、代码版本/最终载荷/授权评测入口定向用例、首問失败的正式重试验收；更新第六条轨迹及持久白名单产物；最终补齐实际命令结果与未验收边界。真实模型语义质量/延迟/盲审仍 UNRUN。

## 切片三交接：正式接线与本地整场验收

上述“进行中”段为历史中间记录，本节为本轮后续实际结果。没有重做前两切片、重录 V2 快照或另建状态系统。

### 实际实现与兼容边界

- `ApplicationService.create_dynamic_interview` → `create_dynamic_role_interview` → `_create_session_from_plan`：新建协议 3 默认明确冻结 `coding_defence_version=1`。可显式 `coding_defence=False` 重建旧契约测试；无标记历史协议 3 不启用，协议 1/2 不写此标记。`_plan_value` 仅在字段确实存在时纳入指纹，恢复不补字段。
- `AppController.submitInterviewCode` → `record_role_coding_answer`：保存原代码一次并冻结 UTF-8 原文、SHA、题目指纹、当前运行版本。`coding_defence` 保存父题、子题列表、pending/answering/closed、关闭原因及候选剩余秒数。语法未完成不阻止对已存在代码取证；无原文时记录 no_code_evidence，不编造代码。
- `submitInterviewAnswer` 按 kind 区分代码与口述；子题 stage=coding、kind=oral、独立 q-ID 及 parent_coding_question_id。`advance_dynamic_role_interview` 分派到 `coding_defence.advance`，复用 `interviewer_state.merge_decision`、请求快照、来源范围、原子 `_save`。问题合法落盘才计数和展示；不重新锁定、不回 theory、不另选 coding。
- `coding_defence.sources` 注册 code:q-ID / run:q-ID / test:q-ID / 子题 q-ID，区分代码、版本绑定自测、公开测试、口述。引用由本地查连续原文与 SHA；代码不去缩进、不修补反引号。旧版本运行结果明确 matches_locked_code=false，既不丢弃其来源，也不冒充当前代码已验证。
- `validate_saved_sources` → `coding_defence.validate/sources`：恢复重查父题指纹、锁定原文 hash、子题集合、关闭原因和引文，不从编辑器缓冲区恢复来源。父题代码锁定后，业务保存/运行/重新锁定入口均拒绝，不能只靠隐藏按钮。
- `build_role_interview_context_preview`：首问没有伪造口述回答；发送冻结题面与 typed code sources。专业方法强制包含 code-defense-failure-analysis，另一个按实际代码、最新解释与缺口选择；仍最多两个。题目匹配的 coding_review 先经 task SHA 检验，不匹配则不加载；通用专家参考只取有相关信号或题目 review 指向者，不把每题硬套到八个主题。
- `next_stages` 保留四大阶段，coding 内允许答辩；`MIN_REMAINING_SECONDS=60` 使用现有 Session 时钟，不增加时长。59/60/61 验收；AI 等待与暂停重叠不重复扣候选时间。已到收尾边界时构建器拒绝生成请求，保留数据，不假装解析成功。
- 第二答在 `_store_answer` 完整锁定后以 question_limit 关闭，不额外请求 finish；未在线判断的最后一答不写 model_supported。第一答可在同一次生成事务中认可后结束，或留下具体缺口再问；诚实未知只能沿既有 adjacent 规则换角度，不能认作支持。
- `finish_role_interview` 幂等收尾；父 coding 题独占原 rubric、原维度与 0.3 权重，子题不进入独立评分队列。`update_finished_grading` 校验聚合来源引文；独立给子题评分的业务入口和构建器均拒绝。口述“应该改成”不会改变代码/执行事实。
- `interview_result_view` 和 report.json/report.md 保留父题、答辩原文、来源、状态和关闭原因；旧代码运行版本显式提示。未答辩不新增零分维度。完成过的父题评分不重评，重启保留待评分队列。
- 正式 QML 只增加“查看锁定代码”的只读区，仍用现有文字/语音输入、历史、重试、结束和报告路径。没有新页面、语音模型或视觉重构。

### 本轮实际发现并修复的问题

1. 正常 Codex 响应回调尚未释放就调用结束，结束入口又尝试 interrupt 已完成请求。Fake 整链暴露为 defence 已关闭但 Session 未结束。改为在回调清理后排队执行正常 finish，并绑定 Profile/Session 防止切换污染；用户主动结束仍即时取消。
2. 用户在 Codex 生成中结束时，采用原有精确 turn fence 并等待停止确认；不接纳晚到正文。停止确认后恢复已有评分队列，不要求重连、不重复评分。
3. 旧版本运行记录保留后，原显示文案会被误读为当前代码通过；现已标出旧版本，不改变客观结果。
4. 答辩到时使用已有 finish 保存未完成记录；未提交草稿仍按草稿语义保存，不冒充锁定回答。已提交口述不会丢失。

### 可复现运行记录（全部 Fake/脚本，不是远端服务测量）

| 路径 | 下一问生成 | 结束评分 | 代码执行 | 结果 |
|---|---:|---:|---:|---|
| Provider 一问结束 | 5：前序 3 + 答辩 2 | 4 个父评分单元 | 0 | q-005 回答后正常结束 |
| Codex 一问结束 | 5：前序 3 + 答辩 2 | 4 | 0 | 同一正式事件链完成；无额外 finish 调用 |
| Provider 两问结束 | 5：前序 3 + 答辩 2 | 4 | 0 | q-006 最后一答本地结束，无下一问请求 |
| Provider 首问坏引文后原位重试 | 6：含一次失败生成 | 4 | 0 | 父代码只锁定 1 次，只生成 1 个合法子题 |
| 59 秒时间跳过（业务脚本） | 答辩 0 | 4 个脚本评分结果 | 0 | 子题 0，原权重；脚本统一 3/5 得 50 分 |
| Codex 生成中用户结束 | 启动 4，最后一个取消 | 4 | 0 | 晚到问题不接纳，子题 0，确认停止后评分 |

前四条“生成”包含已完成前序问答；时间跳过行只计答辩阶段，其前序通过正式业务事务布置。Fake 给出的 3/5 仅检验队列、引用与权重，不代表候选代码正确、测试通过或真实模型评分合理。

累加片段测试的提交前后 SHA 相同：`c22e62ed1bf1d03d48e4a5f30a9fcca74bae6b44fa816064e53968bf28db8e4d`。持久 trace 的 parent q-004 权重均为 **0.3**；q-005/q-006 不另加权。

另用实际候选 **LOSS-014** 的三份合成代码分别验证核心张量逻辑、局部归约问题、带语法缺口但有 logsumexp 逻辑的部分实现。三份均由生产候选选题、保存、锁定、编译、引文事务进入答辩，真实运行资产检查通过，但本轮 **没有执行这些代码或公开测试**。审核侧区分三种输入，不向模型发送预期错误标签。

### 实际测试命令与结果

以下均为受影响的定向测试，互有覆盖重叠，不相加声称独立案例数量。

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence.py tests/infrastructure/test_interviewer_eval_transport.py -q -s --maxfail=2 --junitxml=workspace/maintainer/evidence-driven-interviewer/slice3-service-final.xml
# 13 passed in 368.68s（此后新增的 clock 用例另行执行，见下）
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence_desktop.py -k provider -q -s --maxfail=2
# 3 passed, 1 deselected in 278.80s（当时参数集）；一问/坏引文重试/两问
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence_desktop.py -k 'codex_end or time_deferred' -q -s --maxfail=1
# 2 passed, 5 deselected in 149.98s；主动结束生成、到时收尾
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence.py::test_defence_wait_pause_and_resume_share_session_clock tests/infrastructure/test_coding_defence_desktop.py::test_existing_unmarked_protocol3_still_finishes_on_code -q -s --maxfail=1
# 2 passed in 89.60s；共享时钟/暂停重叠、无标记历史协议3正式提交即结束
$env:LLM_LAB_EVIDENCE_ARTIFACT_ROOT = Join-Path (Get-Location) 'workspace/maintainer/evidence-driven-interviewer/defence-traces'
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence_desktop.py -k 'whole_chain and (provider_two or codex)' -q -s --maxfail=1 --junitxml=workspace/maintainer/evidence-driven-interviewer/defence-traces-final.xml
# 3 passed, 4 deselected in 286.55s；保存两問/一問/主动结束的完整合成传输产物
.venv\Scripts\python.exe -X utf8 scripts/evaluate_interviewer_expertise.py --output workspace/maintainer/evidence-driven-interviewer/slice3-48
# 48/48 编译通过，network_calls=0；已存在此目录时请使用新的隔离输出名
```

其他已执行：首轮取消/写入失败/晚到/重复/结束专项 **1 passed / 66.15s**；LOSS-014 三份代码 **3 passed / 82.96s**；长代码最终载荷与超限保留 **1 passed / 35.74s**；旧 V2 快照、旧编码提交结束、原暂停快照三个兼容用例通过。原五条非答辩轨迹保留其此前通过记录，本轮未重跑全部五条。

失败如实记录：测试最初误用不存在的 Problem.track；修正为真实候选对象。Codex 整链先修正 Fake 投递须匹配具体 turn ID，随后定位并修复上述真实收尾问题，复验通过。长回答超限测试最初使用超过产品 50,000 字符上限的输入，被提交层正确拒绝；改为合法长度但超上下文预算的已锁定回答，原文保留与预算拒绝通过。未放宽生产契约或以改基线消除失败。

### 预算、来源与持久验收产物

- 继续上限 64,000 Unicode 字符 / 160,000 UTF-8 字节，不称 token。最新长代码用例在冻结代码原文不变的前提下，最终序列化 Provider 消息为 **39,910 字符 / 73,556 字节**，Codex prompt+schema 序列化包为 **44,691 / 78,337**。这不是完整 HTTP 帧，也不是真实模型延迟。超额的完整口述不截断、不发送；锁定代码保持原 SHA。
- 本轮 48 场景业务对象最大 **32,028 字符 / 49,130 字节**。从原提交导出的旧版与本轮输入 **48/48 id/input_sha256 配对一致**。未重录 V2 baseline。Codex 线程累计上下文仍不可由单轮上限保证，未换线程/模型规避。
- 持久位置：`workspace/maintainer/evidence-driven-interviewer/`，`git check-ignore` 已确认受现有规则忽略。`baseline-48/` 与 `slice2-48/` 各仅复制 summary + 48 request + 48 review-only 共 97 个明确合成文件，并写 manifest；不扫描/复制整个 TEMP 或 Profile。
- `slice3-48/` 是本轮离线运行器直接生成的新合成请求、sidecar、输入 hash、资源版本和度量。`defence-traces/` 保存 codex / provider_two / codex_end 的实际 Fake 请求、脚本响应、父权重、答辩状态和 SHA manifest；三份文件 hash 已重新核对一致。
- 同目录的 junit XML 保存真实命令结果与合成计数；包含曾经失败的 compat-budget.xml，后续成功结果在 defence-budget.xml / slice3-service-final.xml，不用覆盖全部失败记录装作从未失败。

### 经授权真实对照的入口与剩余边界

`scripts/evaluate_interviewer_expertise.transmit_authorized_case` 是显式的程序调用入口，不是 `--responses` 的别名：调用方提供现有已配置 Provider adapter，或独占事件消费的 Codex backend/thread；函数不查询、存储密钥，不读取档案。默认 execute=False 只返回实际载荷、参数、度量和确认 hash；execute=True 必须匹配逐场 payload+模型/推理参数的 hash。Provider 配置必须与 descriptor 一致，Codex 沿用显式线程与参数，不接管正在面试的事件流。Fake Provider/Codex 各验证 0 次默认发送、错误确认 0 次、正确确认 1 次、参数改变后拒绝；结果保留原文供离线回放审核，semantic_quality 仍 UNRUN。

没有新增设置页中的在线评测按钮或自动取得连接的 CLI；以后真实对照需要维护者显式传入现有 adapter、合成 preview/instruction 和对应版本解析契约。此程序接口已验证，但尚未进行真实连接端到端运行，不能称真实对照已通过。

本轮修改清单（在已有切片1/2脏树上继续，不是相对 HEAD 的全部文件）：新 `coding_defence.py`、`test_coding_defence.py`、`test_coding_defence_desktop.py`、`test_interviewer_eval_transport.py`；续改 `application.py`、`role_interviews.py`、`interviewer_state.py`、`interview_flow.py`、`interview_expertise.py`、`ai/context_builder.py`、`ai/interview_context_budget.py`、`desktop/controller.py`、`desktop/qml/pages/InterviewPage.qml`、`workspace/schema/role-interview-session.schema.json`、`scripts/evaluate_interviewer_expertise.py`、第六条 trajectories fixture 和本记录。未再扩建方法包或八张知识卡。

真实模型语义质量、真实整场延迟、专家盲审、macOS 实机、真实麦克风/语音识别均 **UNRUN**。本轮 QML 使用正式页面、隔离档案与 Fake 传输，验证只读代码、中文组字、原位重试、口述和结束后的父题评分；不把它描述为全面视觉或真实语音验收。

最终父题评分增量与最后 diff 核对结果另附于下方；全部源码留在工作树，无提交/推送/打包/发布/全量回归/真实模型调用，原有未跟踪内容全部保留。

### 最终核对与精确续接

最后增量：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence.py::test_code_defence_parent_scoring_and_final_answer -q -s --maxfail=1 --junitxml=workspace/maintainer/evidence-driven-interviewer/defence-parent-final.xml
# 2 passed in 130.86s
git diff --check
# 通过；仅继承的 QML LF→CRLF 策略提示，无空白差异错误
```

最后两例还验证：口述保存后重启、结束但未评分时重启、第二答后构建器拒绝额外生成、子题评分上下文被拒绝、父题评分包含最后完整口述，代码 hash 与权重保持不变。

`main` / `b954c71d6a7029010fc247cbf7eef6c880a102f1` 未变。所有新旧源码改动仍留在当前工作树。唯一工程记录已更新；持久合成产物和 JUnit 均在上面的 ignored 位置，不纳入提交。

当前裁决：**SLICE3_LOCAL_ACCEPTANCE_PASSED / REAL_MODEL_QUALITY_UNRUN**。

精确续接位置不再是“coding 提交后直接 finish”：新契约现经 `coding_defence.advance` 完成最多两道答辩，再由既有父题评分入口汇总。若下一轮获准做真实专业质量对照，从 `evaluate_interviewer_expertise.compile_input` 的合成输入、`transmit_authorized_case` 的逐请求确认和既有输出回放契约继续；不要重录旧版快照，不把本轮 Fake 结果计算成语义准确率。未获真实调用授权前不读取连接、密钥或真实材料。

## 切片三有限收尾核对（当前最终续接）

### 实际缺口与最小修改

核对基线仍为 `main / b954c71d6a7029010fc247cbf7eef6c880a102f1`，保留全部已有脏树。没有重新实现切片三。本轮相对进入时仅修改 `desktop/controller.py`、`tests/infrastructure/test_coding_defence_desktop.py` 和本记录。

1. **关闭已落盘、排队 finish 未执行的重启窗口确实缺失。** 原父题测试在结束之后才恢复评分，并非此窗口。补测通过真实 service 锁定代码、生成子题、提交口述、关闭答辩；刻意不调用 finish，再新建 Controller，修复前两种路径均恢复成 active。现在 `_load_interview` 在读取/校验有效的新契约 closed 答辩、无忙任务且无存活 Codex 请求身份时，复用 `service.finish_interview(confirm_incomplete=True)` 幂等完成已承诺的收尾。存活响应仍先清理自身 operation，再沿原排队 finish；不新建恢复状态、不补历史标记、不生成问题或语义判断。
2. **主动结束缺停止确认时，实际源码与上一轮记录有差异。** 原 `finishInterview` 对 Codex 调用 `stopInterviewGeneration`，已知 turn 的 `cancelCodex` 只发 interrupt；已有“精确 fence + 5 秒超时断连”未被此分支使用。旧确认成功测试没有揭示此遗漏。新测试先证实 fence=false；最小修复是该分支调用已有 `_cancel_coach_stream_for_reload`，Provider 保留原停止入口。结束仍立即保存，不等网络确认；未确认时 `_start_pending_grading` 拒绝抢跑，精确确认后正常继续；缺确认则由原 `_expire_codex_drain` 使旧连接离线，等待正常重连，不接管其他消费者。

未修改业务协议、题目/方法资源、评分逻辑、Provider、计时、QML 或模型配置。

### 两个窗口的可定位证据

测试文件均为 `tests/infrastructure/test_coding_defence_desktop.py`：

- `test_restart_after_defence_closed_before_queued_finish[False-3]`：一问后脚本决策 finish 已落盘，未执行 GUI finish；新 Controller 自动收尾。
- `test_restart_after_defence_closed_before_queued_finish[True-3]`：第二答已本地锁定并关闭，未执行 finish；新 Controller 自动收尾。两例在 332–342 行断言 Session 结束、最后原文不变、questions/answers/state/defence 全等、最后一答未虚增 applied_answers、只有 q-001～q-004 四个父评分单元、重复加载/结束不再写入。生成/重锁入口设置失败哨兵，恢复未调用。评分发送在此两例禁用，仅验证持久队列，不冒充在线评分；父题评分正确性复用整链测试。
- `test_formal_coding_defence_whole_chain[codex_no_ack-3]`：正式 QML + Fake Codex 从前三轮到代码锁定、首问生成中主动结束。123–145 行验证 fence 和 busy、user_end 与代码 SHA、确认前零评分、错误 timeout token 无效、正确 token 触发原超时断连、迟到终止不改 Session、新 Controller 保留结束状态与相同四项队列。这里显式执行既有计时回调，不靠固定 sleep 碰顺序。连接断开由该真实 timeout 路径触发；重启使用新 Controller/Service 读取同一合成档案，不宣称已执行 OS 强杀或真实 App Server 崩溃实验。
- 原 `test_formal_coding_defence_whole_chain[codex_end-3]` 保留停止确认成功后评分路径，复测见下。无确认与有确认两条路径都不允许晚到题面落盘。

持久证据 `workspace/maintainer/evidence-driven-interviewer/finite-audit-traces/`：`codex_no_ack.json`、`restart_closed_one.json`、`restart_closed_two.json` 及对应 SHA manifest。全部由明确合成 fixture 产生，不复制档案目录。恢复 trace 的 exchanges 为空表示**恢复阶段零传输**，不是抹去其之前用 service 脚本构造的问答；完整保留断言在测试/JUnit。

### 准确的调用计数与第六条轨迹映射

以下前三行复核既存 `defence-traces/*.json` 及 manifest，未重录；生成决策和评分由 response 的实际解析契约区分。全部为 Fake 计数。

| 持久 trace / 实际路径 | 问答决策请求 | 已展示答辩问题 | 专用于结束语的请求 | 最终评分请求 | 代码执行 |
|---|---:|---:|---:|---:|---:|
| `codex.json` / 一问结束 | 5：前序3 + 首问1 + 第一答处理并结束1 | 1 | 0 | 4 | 0 |
| `provider_two.json` / 两问结束 | 5：前序3 + 首问1 + 第一答处理并追问1 | 2 | 0 | 4 | 0 |
| `codex_end.json` / 生成中主动结束且确认停止 | 发起4，完成3；第4次取消 | 0 | 0 | 4 | 0 |
| `finite-audit-traces/codex_no_ack.json` / 无停止确认 | 发起4，完成3；第4次无完成结果 | 0 | 0 | 0（四个父项保留 pending） | 0 |
| `restart_closed_one/two.json` / 仅恢复阶段 | 0 | 不新增，分别保留1/2 | 0 | 0（本例不发送评分） | 0 |

`codex_end.json` 的 exchanges 只有 3 个完成的决策响应，不能误记为仅发起3次；原 JUnit 的 `generation_started=4 (last cancelled)` 和测试 `len(queued)==8`（4决策+4评分）共同证明启动口径。一问结束所需的第二次答辩决策不删除，它用于处理第一答并作状态事务；不是独立结束语调用。两问路径 `len(generation)==5` 且最终包含 q-006 原文，证明第二答后只发生原父题评分，无新增问答决策。

第六条 fixture `interviewer-expertise-trajectories.json / coding_defence` 对应实际完整 node ID：

| 实际 node ID（前缀均为 `tests/infrastructure/test_coding_defence_desktop.py::`） | JUnit | 持久合成 trace |
|---|---|---|
| `test_formal_coding_defence_whole_chain[codex-3]` | `defence-traces-final.xml`；本轮 `finite-audit-shared.xml` | `defence-traces/codex.json` |
| `test_formal_coding_defence_whole_chain[provider_two-3]` | 同上 | `defence-traces/provider_two.json` |
| `test_formal_coding_defence_whole_chain[codex_end-3]` | 同上 | `defence-traces/codex_end.json` |
| `test_formal_coding_defence_whole_chain[codex_no_ack-3]` | `finite-audit-after.xml` | `finite-audit-traces/codex_no_ack.json` |
| `test_restart_after_defence_closed_before_queued_finish[False-3]` / `[True-3]` | `finite-audit-after.xml` | `finite-audit-traces/restart_closed_one.json` / `restart_closed_two.json` |

表内相对产物路径均以 `workspace/maintainer/evidence-driven-interviewer/` 为根，受既有 ignore 保护。原三份 trace 的 SHA manifest 全部复核一致，父 q-004 权重均0.3，锁定代码 SHA 均为 `c22e62ed1bf1d03d48e4a5f30a9fcca74bae6b44fa816064e53968bf28db8e4d`；子题不另加权。时间跳过仍复用 `test_coding_defence.py::test_defence_time_boundary[59]` 与 `slice3-service-final.xml`，不为本轮映射重新建设第六条轨迹。

### 定向测试与停止边界

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_coding_defence_desktop.py -k 'restart_after_defence_closed or codex_no_ack' -q -s --maxfail=3 --junitxml=workspace/maintainer/evidence-driven-interviewer/finite-audit-before.xml
# 修复前：3 failed, 8 deselected in 76.74s；保留失败产物。
$env:LLM_LAB_EVIDENCE_ARTIFACT_ROOT = Join-Path (Get-Location) 'workspace/maintainer/evidence-driven-interviewer/finite-audit-traces'
# 相同 pytest 选择，JUnit 改为 finite-audit-after.xml：
# 修复后：3 passed, 8 deselected in 78.42s。
.\.venv\Scripts\python.exe -X utf8 -m pytest 'tests/infrastructure/test_coding_defence_desktop.py::test_formal_coding_defence_whole_chain[codex-3]' 'tests/infrastructure/test_coding_defence_desktop.py::test_formal_coding_defence_whole_chain[codex_end-3]' 'tests/infrastructure/test_coding_defence_desktop.py::test_formal_coding_defence_whole_chain[provider_two-3]' tests/infrastructure/test_coding_defence_desktop.py::test_existing_unmarked_protocol3_still_finishes_on_code -q -s --maxfail=1 --junitxml=workspace/maintainer/evidence-driven-interviewer/finite-audit-shared.xml
# 4 passed in 97.39s；Codex正常/确认停止、Provider两問、无标记历史协议3。
```

本轮未改上下文编译路径，所以没有重跑48场景、重录V2、或重跑五条非答辩轨迹；原48场景只证明离线编译/输入隔离，不是语义质量评测。真实模型、真实延迟、专家盲审、macOS 实机、真实语音与 OS 强杀恢复均 UNRUN。未调用 `transmit_authorized_case` 真实发送，未读取真实档案/材料/密钥，无子 Agent、提交/推送/安装/构建/发布或全量回归。

完成有限核对后停止扩展结构。后续仅在新授权任务下继续；本轮不自行发起专业质量对照。

最终 `git diff --check` 通过（只有继承的 QML LF→CRLF 策略提示）。新三份合成 trace 的 manifest 与实际 SHA 核对一致；此前失败 JUnit 未覆盖。当前裁决保持 **SLICE3_LOCAL_ACCEPTANCE_PASSED / REAL_MODEL_QUALITY_UNRUN**；切片三有限收尾完成，不再扩展实现。当前 main/HEAD 未变，所有原有及本轮修改留在工作树。

## 2026-09-11 两处定点修复

起始 HEAD 为审查提交 `e5f89af359ad5f7c1c54886b0903d688d4d1a660`，相关已跟踪文件无未提交修改；原有未跟踪资产不动。本轮不是新切片。

- **A 原因与修改**：Context Builder 在专家非空时覆盖知识 ID，预算模块又无条件删除普通候选。删除前者；后者保留原普通池、按 card ID 保序去重，不因同 topic 专家 criterion 存在而删卡。每次预算循环均从实际保留的普通卡和专家参考重算白名单，再序列化、计算 ContextPart hash。超预算仍先裁旧历史/最近历史、再裁可选候选；必需内容超限仍拒绝。未改排名、上限或答辩资源优先级。
- **B 原因与修改**：全文首次匹配抢占范围内后续匹配，而且预校验之后会再次全文定位。`anchor` 增加可选 source_scope，验证来源 hash 和原始半开区间，在所有允许区间先选最早精确匹配，之后才允许口述的反引号兼容；code/run/test 严格匹配。`merge_decision` 局部复用同一定位结果，覆盖经历、主张、矛盾、显式及自动关闭。历史已存位置不迁移，恢复仍按位置校验。
- **直接调用兼容**：`role_interviews.py`、`coding_defence.py` 各一行将协议3缺失/None范围转为空授权范围，避免误走 anchor 无范围兼容路径；不是修改时钟、评分或答辩流程。其他生产修改仅 `ai/context_builder.py`、`ai/interview_context_budget.py`、`interviewer_state.py`。
- **复现与测试**：新增 `tests/infrastructure/test_interview_resource_scope.py`。B 首次即复现误拒绝；A 的合成问答最初误命中“组内优势/缩放”专家主题，移除这些非目标词后确认所有参考 priority=3，仍因缺少 knowledge_candidates 抛出 StopIteration。修复后真实 EGT-QB-002 普通卡与专家兜底共存并可用于事务；同主题普通卡也保留，预算裁掉普通卡后其独有 ID 拒绝、仍有专家的 ID 保留。两种最终传输序列化均检查同一 contract 和原预算，ContextPart hash 与实际内容一致。
- 引文正例经合法历史经历/矛盾/关闭流程提交，当前主张仍只能引用当前回答；逐项验证保存的是后一次原始位置、decision 未修改、旧引文不重定位、恢复成功。空/缺失范围、错误 hash、范围外、分段拼接、历史回答冒充当前主张均整轮拒绝，Session/revision/下一问不变。轻量参数化覆盖精确匹配优先、反引号兼容、最早合法位置、非法区间和代码/运行/测试严格匹配。

实际命令：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interview_resource_scope.py tests/infrastructure/test_interviewer_evidence.py::test_v2_compiled_baseline tests/infrastructure/test_interview_expertise.py::test_grpo_compiled_expertise_and_scripted_transaction tests/infrastructure/test_interview_expertise.py::test_long_actual_compilation_rejects_unsent_old_quotes_and_overflow tests/infrastructure/test_coding_defence.py::test_defence_rejected_sources_restart_and_atomic_retry -q --maxfail=2
# 27 passed, 1 failed in 75.54s。唯一失败为新测试把回答文件hash误当作去文件格式后的文本hash。
# 对照既有 _locked_answer_text 契约，断言改用已校验的锁定记录hash；不修改生产存储或指纹。
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/infrastructure/test_interview_resource_scope.py::test_repeated_sent_quotes_persist_same_locations_in_all_updates -q
# 1 passed in 8.36s。仅重跑修正断言的用例，其余27例未重复运行。
git diff --check
# 通过。
```

未运行48场景全集、桌面整链、全量回归、真实模型、真实延迟或专家盲审；未重录V2快照。无子Agent、真实档案/材料/密钥读取、依赖安装、提交/推送/构建/发布。真实语义质量继续 UNRUN。本轮两处定点修复完成，到此停止。
