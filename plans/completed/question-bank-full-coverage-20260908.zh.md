# 题目.md 全量练习与面试接入

## 目标

对用户提供的 40 项手撕、160 项八股逐项建立可核查映射：手撕有真实可运行练习，八股有可作答、再核对要点的练习入口；动态面试可从相关岗位内容中选取和追问，不只是文档索引。重复题允许合并，但源条目不得遗漏。

## 仓库事实

- 基线 `36d0a8f98a5f4c12b5bc4a67d2563ce1fdaf3cc1`，分支 `fix/dynamic-interview-full-flow-20260905`；已有 76 个可推荐代码题、120 张知识卡。
- 本轮授权输入：根目录 `题目.md`，SHA-256 `4b9be92238921f4b8f06613a8164aa814ed8b1bb55b3081b83011da6e33f80bb`。其中 Obsidian 图片引用不等于已经提供图片正文，不能猜测其公式。
- 开始时无 tracked 未提交改动；全部原有未跟踪文件、UAT、真实 Profile 和材料保持不动。源文档保留原样，不作为产品事实源。
- 既有 Catalog 负责 Coding；知识库已有展示入口，但本轮必须验证口述练习交互以及动态面试是否实际使用知识题库。

## 分工与文件所有权

1. Coding Agent：独立 worktree，核对 40 项，补缺失算法/明确变体；只写自己的新题目录、专属 Catalog shard、专属测试。来源映射/私有验算放 ignored 维护者目录；不修改共享 Schema/角色/README。
2. Theory A Agent：独立 worktree，覆盖 T001–T080（训练、RL、架构、PEFT），查一手定义并原创知识卡、追问、评分依据；只写专属内容片段，主控集成共享知识库。
3. Theory B Agent：独立 worktree，覆盖 T081–T160（数据评估、推理系统、Agent、多模态）；同上，和 A 分开来源/条目所有权，交叉重复交给主控合并。
4. 主 Agent：运行入口与内容选题接入、公共知识库合并、覆盖索引、最小 QML/Service 修改、集成和独立验收。三个子 Agent 不得替自己做唯一验收；完成后交叉审内容，主控实际运行定向测试。

## 范围

优先复用已有题目；只新增真实缺口，不批量复制同名题。纠正源问题的绝对化/过时前提，例如混精度不总要 FP16、R1-Zero 无 SFT 冷启动、FlashAttention 不把算术变线性、架构/版本和模型间比较必须说明条件。

不新增岗位、Provider、数据库或通用框架，不改 Mastery，不公开完整参考代码/私有测试，不构建、不发布、不运行全量测试。若涉及新增可持久化口述草稿，仅用现有 Profile 本地机制，不把自评当 mastery。

## 里程碑

- [x] 完整读取并编号，分配互不冲突的三个任务。
- [x] 子 Agent 完成手撕补缺和全部八股内容，主控完成实际练习/面试入口。
- [x] 合并重复主题，生成 C001–C040 / T001–T160 完整对照。
- [x] 交叉内容 Review、真实代码 Oracle、QML 交互与动态选题验收。
- [x] 限定提交为本轮源码、内容、测试和文档，记录实际证据与剩余限制；Git 交付状态以最终回复的远端核对为准。

## 验证

仅运行新增题公开/私有 Oracle、本轮内容覆盖/来源/Schema 测试、口述练习与动态面试 Context/选题定向测试、必要的 QML 加载与真实交互截图，以及 git diff --check。不把 Fake Provider 验证冒充真实服务面试效果。

## 风险与决策

- 原文有重复主题，允许复用同一知识卡，但完整子问题都必须得到覆盖；不以关键词出现判定完成。
- Coding 必须可通过实际环境与岗位筛选；硬前置不能依赖没有可达 Mastery 的节点。教学顺序放推荐路线。
- 来源只保存摘要和链接；不同版本算法保留范围说明，不把缺失的图片当作指定接口。
- 动态面试每次只生成下一问；选题素材不能包含完整未来题单或把答案提前显示给候选人。

## 进度与复盘

### 实际交付

- 40 / 40 手撕、160 / 160 八股已逐项映射至 [机器可校验索引](../../curriculum/interviews/question_collection_20260908.json) 和 [完整用户对照](../../docs/content/question-bank-coverage.zh.md)。原图片正文未提供的项目明确写出数学变体，不伪称复制了图片公式。
- 补齐 8 个代码缺口：ATT-001、NNL-018、NNL-019、TNS-018、LOSS-017、ATT-023、ATT-024、VLM-015。其中 ATT-001 沿用原规划 ID，另外 7 个新增。采用既有 Catalog、题目资产和 Grader；现有 5 条推荐路线及 Skill 反向索引接入这些题。
- 重复主题合并成 135 张完整新知识卡；当前 255 卡、258 条来源记录。所有原始 T 编号可检索，并保留原问题子项覆盖说明。基线 120 卡和 135 条来源经 YAML 语义比较，无删除、无字段改写。
- 知识库新增「独立回答 → 保存 → 核对要点」真实交互及关联代码入口。草稿只写当前 Profile 的 `knowledge_practice/<card_id>.txt`，不写学习事件，不自动发送 AI。
- 动态面试在允许进入原理阶段时，按当前岗位、回答、已授权背景和已问问题选择最多 8 张公开主问题/追问。Codex、普通 API 共用 `build_role_interview_context_preview`；候选不含参考答案和评分标准，不成为未来冻结题单。

### 审查中实际修复

1. **跨 Profile 草稿串用（P1）**：独立审查以真实 Qt 交互发现切档后仍残留原答案。将详情绑定 `profile_id`，切档清空，保存同时核对当前档案、详情档案和卡号；原失败探针复验通过，新正式测试覆盖重返原档案恢复。
2. **关联手撕入口假可用（P1）**：从 Onboarding 已有任务进入 MLA 卡，按钮最初没有解释「已有未完成代码任务」。现在沿用 `start_problem` 的真实约束返回 `start_blocked_reason`，启动题目后立即更新列表；分别验证阻断提示及无其他进行中任务的真实打开路径。没有取消既有一次一题规则。
3. **知识库条目被截断（P1）**：移除原 200 条上限，255 张卡均可搜索和打开。
4. **当前话题遗漏**：年轻求职者明确回答自己做过高级方法时允许该话题进入候选；不降低评分标准，也不据此编造其经历。
5. **筛选文案（P2）**：把「全部可做」收紧为「已解锁待练」，保留浏览，但不承诺可以绕过当前任务立刻开始；README 同步。

### 定向验证

环境：维护者 Windows / Python 3.11 / PySide6，实际安装的 CPU PyTorch 和 NumPy。全部使用临时合成 Profile，无真实材料、API Key 或私人提交。

```powershell
$env:PYTHONPATH = 'src;.'
$env:QT_QPA_PLATFORM = 'windows'
$env:LLM_LAB_UI_EVIDENCE_DIR = 'workspace/maintainer/question-bank/screenshots'
.venv\Scripts\python.exe -m pytest tests/infrastructure/test_question_bank_coverage.py tests/infrastructure/test_question_bank_runtime.py tests/infrastructure/test_question_collection_coding.py -q
# 20 passed in 68.21s

# 既有知识库领域测试，在前一集成批次执行：8 passed
# tests/infrastructure/test_knowledge.py

.venv\Scripts\python.exe -m pytest tests/infrastructure/test_dynamic_interview_flow.py -k 'context_keeps_resume or conversation_strategy or full_flow_reaches or api_wire_sends_selected_model' -q
# 6 passed, 15 deselected in 32.02s

git diff --check
# 通过；仅 Git 提示 CRLF/LF 转换，不是差异空白错误。
```

- 上述合计 **34 个不同的相关测试通过**，不是一次全量 34-test 运行。独立 Profile 泄漏探针和关联按钮复验另有各 1 passed；不重复计入正式测试数。
- 8 个代码缺口由主 Agent 独立重跑真实参考实现：**61 个公开用例、27 个私有用例通过**。另核实 MQA 的真实 Hkv=1 路径：7 个公开、1 个私有用例通过。私有参考代码与用例只在 ignored 维护者目录，不进入本次提交。
- 覆盖索引测试遍历 40 个主映射的真实环境、8 岗位 × 3 级别候选及可达前置，不用替换环境探测来宣称可达。135 卡均可匹配真实角色并进入实际原理候选选择器。
- 运行实际动态会话：经历问答后进入原理环节，当前 GRPO 回答匹配候选，再只追加一个真实问题。既有局部流程覆盖编程、结果和模型/推理配置传输；服务响应由本地可控 Fake API 提供，不等于真实 Codex/DeepSeek 验收。
- Windows 正式 QML 页面在 900×620、1080×680、1280×800、1440×900 下实际输入、展开、滚动、保存；900 窗口同时采用 125% 字体。使用浅/深主题，验证无 placeholder 重叠、内容行互不遮挡、横向不越界。
- 实际截图保留于 ignored `workspace/maintainer/question-bank/screenshots/`，主 Agent 和独立 Reviewer 查看 900 深色及 1440 浅色。系统 DPI 150%，截图物理像素大于逻辑窗口尺寸；这些是生产页面、合成档案，不是 demo Controller。
- 最终对 README、桌面文档、完整对照及本完成计划检查了 110 个本地 Markdown 文字链接，全部目标存在；提交范围的凭证模式检查无命中，未纳入 UAT 或私人目录。

### 内容独立验收

三个作者分区写入；共享 YAML、Schema 周边索引、README、应用层和 QML 由主 Agent 单独集成。中间片段、搜索记录和长报告只留 ignored 目录，没有把原始材料批量提交。

主 Agent 检查全部 135 张卡的主题/例子摘要，并精读 A 组 19 张与 B 组多模态 12 张；A 作者独立审查 B 组 16 张，Coding 作者独立审查 B 组 11 张（其中 2 张与主 Agent 重叠），B 作者独立审查 A 组 14 个题号对应的 13 张卡。按实际卡 ID 去重，完整独立抽检 **69 / 135 张（51%）**，无未解决 P0/P1；其余卡经过完整 Schema/覆盖测试与主控摘要审阅，但不声称每张均经完整独立精读。

抽检源编号可对照覆盖索引复核：主控 A 为 T001、T002、T004、T014、T021、T025、T026、T028、T030、T037、T040、T042、T059、T063、T064、T066、T067、T068、T072，主控 B 为 T149–T160；A 审 B 为 T082–T088、T090–T094、T096、T097、T104、T105；Coding 审 B 为 T095、T106、T112、T122、T139、T145–T148、T155、T160；B 审 A 为 T005、T006、T008–T010、T012、T013、T015、T016、T019、T020、T022–T024。

来源以原论文、官方源码/文档为主，登记本轮新增 123 条来源记录；不同版本可分别登记，不将记录数冒充不同论文数。B 组新增 81 个 URL 中 80 个可实际打开，1 个 SimHash PDF 直开失败但可取得官方搜索结果；页面打开不等于全文复现。主 Agent另对 MLA、GPT-2、ViT、GSPO、YaRN、ORPO、FlashAttention、Qwen-VL 和 DeepSeek-VL 的关键公式或版本逐项核实。

### 决策与剩余限制

- 不重复新增同名题：例如 MQA 采用验证过的 Hkv=1 特例，activation 三项共用一份明确分函数契约；Pairwise Contrastive 和 InfoNCE、GPT-2 和其他 Decoder、ViT 和 Patch Embedding 则保留不同契约。
- 新 8 题没有 D+2/D+7 变式，因此只承诺可练习、测试和用于面试，不授予 Mastery；前置节点已有真实可达复测资产。
- FlashAttention 练习验证在线 softmax 的分块数学等价，不宣称 CUDA kernel 或实际加速；MLA 是明确边界的教学算子，不等于整套生产模型。
- 本轮没有全量 pytest、CI、Windows/macOS 构建、Release、麦克风测试或真实 AI 服务付费请求，也没有做真实简历面试。远程模型的逐题表现仍需后续 UAT，不能由本地通过替代。
- 键入交互测试使用真实 Qt 键盘事件输入 ASCII，题面和保存内容包含中文；未专门复验 Windows 中文 IME 的全部候选/组合输入状态。
- 源码快照提交到当前功能分支；不合并 main，不动用户已有未跟踪文件。Coding 已集成提交 `f324b41`（`[skip ci]`）；其余提交和远端核对结果在最终交付回复列出。

终局：`SOURCE_CONTENT_INTEGRATED_AND_REVIEWED`。本轮到此停止；真实 AI 面试和用户选题体验留作下一次人工验收，不以此任务名义扩展 UI、STT 或发布工程。
