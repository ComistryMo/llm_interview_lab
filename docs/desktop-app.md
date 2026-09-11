# 桌面应用指南

当前以 **`1.0.1a1` 源码预发布版**迭代，推荐[从源码运行](#源码运行)，本轮不打包。已有 **[v1.0.0](https://github.com/ComistryMo/llm_interview_lab/releases/tag/v1.0.0)** Windows/macOS 下载保留，但不包含本轮改动；历史产物和 SHA 见[发布说明](release-notes-v1.0.0.md)。源码、截图与自动化测试不等于真实 AI、麦克风或 macOS 用户实机全部通过。

历史 Alpha 截图（不代表本轮完成度）：[首页](images/desktop-home.png)、[首次使用](images/desktop-onboarding.png)、[答题](images/desktop-exercise.png)、[模拟面试](images/desktop-interview.png)、[连接](images/desktop-connections.png)。本轮正式页面证据另附候选验收报告，不覆盖这些历史文件。
七个代表页面的深浅主题 Before/After、四尺寸检查和已知限制见 [UI 统一设计与验收](design/product-v1-visual-directions.zh.md#2026-09-08-正式-ui-统一基线-6a1fd20)。这些历史截图的来源不回写；v1.0.0 正式页面见[本版截图](design/desktop-candidate-20260909.zh.md)。

## 统一难度工作台（v1.0.0）

新建动态面试不再区分实习、校招或有经验：选择目标岗位、简单/标准/困难与时长即可，默认标准、60 分钟，之后恢复本档案上次的选择。旧会话和已保存记录保留原协议，不批量改写。

首页优先开始/继续面试，面试页可查看历史记录；当前练习仍可从首页或刷题训练进入。Practice 与手撕共用带行号、原生 Python 高亮、缩进和滚动的轻量编辑器。运行代码是执行自己的 Python 脚本，公开测试单独记录，两者不等同于掌握。

提交后优先生成下一问，详细评分留到结束；AI 等待不扣候选人的时间。经历和原理按证据覆盖与可用时间推进，不设最低轮数。16 张知识卡加入深入、薄弱回答和反例分支，12 道手撕补充中文说明及核心逻辑评价点；报告链接到实际知识与练习入口。实际验收、性能与剩余失败见 [执行计划](../plans/active/unified-difficulty-interview-workbench.zh.md)，其中历史真实 DeepSeek 高推理失败仍未宣称解决；v1.0.0 包含该迭代的实现，不新增真实传输验收结论。

桌面版是普通学习者的推荐入口。它使用 PySide6 + Qt Quick，并直接复用与 CLI 相同的 Catalog、Workspace、Planner、Grader、面试引擎与生命周期；普通业务不会调用 CLI 子进程，也不会解析终端输出。

## 安装选择

| 平台 | 文件 | 说明 |
|---|---|---|
| Windows 10 / 11 x64 | `LLMInterviewLab-Windows-x64-portable.zip` | 推荐，完整解压后运行 `LLMInterviewLab/LLMInterviewLab.exe` |
| macOS 14+ Apple Silicon | `LLMInterviewLab-macOS-arm64.dmg` | 推荐，拖入 Applications |
| macOS 14+ Apple Silicon | `LLMInterviewLab-macOS-arm64.app.zip` | 适合直接解压与自动化验证 |
| 开发者 | 源码安装 | 支持调试、完整可选依赖和贡献流程 |

Intel Mac 没有经过真实 Artifact 启动验证，本版不提供 x86_64 或 Universal2 下载承诺。平台细节见 [Windows](windows.md) 与 [macOS](macos.md)。

## 首次启动

两步即可开始：

1. 输入学习档案名称；
2. 从八类岗位中选择目标岗位。

完成后应用会直接进入首页或第一道可用题目，默认使用 No-AI。能力自评和 AI 连接可以稍后补充；自评不授予掌握状态。新面试不要求求职阶段，也不读取旧档案中的分档标签。

应用会记住最后一次正常使用的学习档案。下次启动会直接恢复该档案，不会悄悄创建新的档案；如果档案缺失或损坏，页面会给出错误编号和“打开设置切换档案 / 重新创建”的处理入口。设置中的学习档案切换器只读取档案元数据；当前答案未保存或仍有录音、测试、前台 AI 请求时，切换会被阻止并提示下一步。已结束面试的后台补评分不锁住档案切换，切换时会停止旧请求，未完成题目仍留在原场次。

## 页面

### 首页

首页主动作是“继续面试”或“开始面试”，下方提供当前练习、最近面试和复盘入口。没有历史时显示引导，不用一排零分指标占据首屏。独立的常驻“答题工作区”导航已移除，但从刷题、当前任务与报告仍可进入真实作答页；不会清空进行中的练习。

重启后若恢复了旧面试的待评分任务，首页会说明评分进度，并提供停止与继续入口。补评分不会让右上角与“开始面试”一起转圈，也不妨碍进入练习或准备下一场。开始或打开另一场面试时会暂停旧评分，避免争用面试请求；之后可从原面试报告继续，已成功评分的题目不会重复请求。停止只取消后续处理，已经发送给 AI 的内容无法撤回。

停止评分后，本次运行不会自动继续；重新启动应用仍会按原有授权恢复未完成评分。授权范围发生变化时先确认，不自动扩大材料范围。模型服务本身的响应时间不因本次界面修复而缩短。

正式页面实图：[首页·浅色](images/unified-interview-20260908/home-light.png) / [首页·深色](images/unified-interview-20260908/home-dark.png) / [准备面试](images/unified-interview-20260908/setup-light.png)。使用隔离合成档案，不含真实材料；[截图清单](images/unified-interview-20260908/manifest.json)记录来源、尺寸和 SHA。旧[训练首页](images/home-polish-20260907/home-practice-light.png)保留为历史对照。

### 求职材料

只添加你拥有、已脱敏且确实需要的文件。文件存在不等于 AI 可以读取；每场面试必须对 material ID、用途和当前 SHA-256 重新授权。文本型 PDF 会提取正文，DOCX 会提取段落和表格，并生成绑定原文件 SHA-256 的只读文本快照；扫描 PDF 暂不做 OCR。无法提取的 PDF / DOCX 仍可仅保存在本机，不能授权给 AI。

### 刷题训练

默认展示岗位推荐路线。答题工作区包括题面、答案编辑器、公开测试、提交、契约审查、口述答辩和 D+2 / D+7。当前源码已移除 AI 辅助页面、侧栏入口及练习页 AI 面板；AI 只用于面试。已有教练历史文件不删除，旧 CLI 保持兼容。

### 模拟面试

选择岗位、简单/标准/困难、时长与面试官。动态面试先显示本地“自我介绍与经历概述”，不等待 AI 生成整场题单。回答后只点击一次**“提交并继续”**：保存回答 → 流式显示下一问 → 校验并冻结 → 继续回答。生成中只显示问题正文，不显示内部 JSON、推理或评分；通过校验后才能正式回答。“已展示 N 问”不是整场总题数。

同一学习档案会记住岗位、难度、时长、面试官、API 连接和材料选择，准备页默认显示摘要，修改时就地展开。没有已保存设置时默认标准、60 分钟；旧档案的求职阶段不参与新面试。不同档案分别保存，已删除连接不会被悄悄替换。模型与推理强度使用已保存值，Key 仍只在系统密钥环。记住材料选择不等于永久授权，新场次仍须明确确认发送范围；远程语音另需授权。

开始前一次确认本场发送范围：岗位与难度、个人背景、主动提交的回答、前序问答和明确授权的材料。已授权范围不变时不重复弹窗；旧场次尚未授权、材料/背景/接收服务改变时需要重新确认。可随时点击回答区的“发送范围”查看，不会因此发送请求。请求失败后回答保留，点击“重试生成下一问”即可，无需重新填写或再次保存。

作答页上方连续展示已发生问答，下方保持稳定回答区。提交后会定位到新问题的开头，不再停在上一轮回答，也不会跳过长题目的开头；平时阅读历史不会被普通状态刷新打断，可点“回到最新”。长回答独立滚动。标题旁无多余“详情”，语音模型与转录设置收进次级区域。准备页与回答区主动作保持可见，小窗口可滚动；“结束本场”仍需确认。

**简历 / JD 是否每轮发送？** 是。勾选「每轮附带已授权的简历 / JD」时，Codex 和普通 API 的每次回答请求都会附带本场授权材料的提取文本，不是只在开场发送；不会重新上传原 PDF/DOCX 文件。授权范围不变时不重复确认，不等于材料只传一次。取消勾选后，新请求不再附带材料全文；前序问答仍会作为对话上下文发送，已经发送的内容也无法收回。本次仅明确提示，没有改变材料授权或请求内容。

动态面试不要求先填自评分数；固定面试的自评与人工证据入口仍保留。回答锁定后不可改写，新的问题使用空白回答框，已提交的回答仍保存在原题。输入框获焦时提示立即隐藏，中文输入法组字时也不会与提示叠在一起。点击「语音输入」即开始录音，状态、时长和「完成录音」紧邻回答区；结束后自动转文字，模型等选项收在「语音设置」中，不会强制滚动题面。

结束后立即保留完整问答记录，后台逐题评分。复盘先显示有证据的表现、三个优先缺口与下一步练习，再展开分数、来源与置信度。缺口可回看原问答、打开知识卡或真实练习；未解锁、未验证或环境不可用会说明原因。已成功评分不重评，失败可单题重试或继续剩余队列；重启可恢复待评分任务，授权范围变化则先确认。没有证据仍未评分，不重新归一化把部分分数做高，也不改写 Practice/Mastery。

逐轮请求包含岗位技能、所选难度、本场历史问答、当前回答和获准简历/JD；不注入旧分档或目标等级。模型先听经历，再沿实现、选择依据、验证与反例追深，取证充分后换角度；答不上来可以换具体例子，不重复盘问同一未知点。之后进入岗位原理，再从真实可运行候选中选择手撕。只冻结已经展示的问题，不预生成未来题单。

手撕题面、接口和公开测试仍由本地 Catalog 冻结；编辑器可以自由运行 Python 脚本，不要求先跑单元测试。写完函数后可以构造列表或张量、调用函数并 `print`，也可在「设置标准输入」里提供 `input()` 所需数据。模型不能任意编造题目或宣称测试通过。新动态面试的 AI 代码评价按核心逻辑、解释和自测证据分别评分；未写完、未运行或局部运行错误不等于所有维度只能得 1 分。代码主观评价与本地执行、公开测试事实分开，不改变 Practice mastery。动态报告按阶段分配权重，不因多问几次就重复计算整个环节的权重。

中文界面下，已有英文题使用与原文 SHA 绑定的中文说明；[AI 手撕 40 项专项](content/ai-handwriting-40.zh.md) 中新写的题面本身就是中文，函数签名与代码保持原样。“查看英文题目”仅适用于有英文原文的旧题；设置中可选择 English，但新中文题尚无完整英译。历史 Session 的原文不被覆盖；原文变化时不套用旧翻译。

本专项已接入现有刷题入口和模拟面试的真实 Coding 候选。算法岗新增 Transformer/数学基础推荐顺序，后训练岗新增损失与 RL 路线，推理岗新增解码/缓存路线；视觉与推荐评测按背景选用，不把所有 40 项强加给所有岗位。知识库搜索 `AI01`–`AI40` 或技术名可查看公式边界、四层追问和来源。

新增[题目集对照](content/question-bank-coverage.zh.md)覆盖用户整理的 40 项手撕、160 项八股。进入「刷题训练 → 知识库」，按技术名或 `T001`–`T160` 搜索，先在回答框独立作答，点击「核对回答要点」后再看机制、推导、追问和分层标准；切题或展开要点时保存当前回答，也可以点「保存回答」。已保存的内容位于当前 Profile 的 `knowledge_practice/`，重开同卡可以继续，不生成 Practice 掌握事件，也不会自动发送给 AI。

动态模拟面试的原理环节会收到最多 8 张本轮相关的公开候选题及追问，候选集合随当前回答更新，不是必须依次完成的固定题单；开场和前期经历深挖不会携带整个知识库。Codex 与普通 API 共用这一上下文。模型仍须一次只问一个问题、引用当前回答评分，不得把知识题当成候选人真实经历，也不能凭知识卡宣称代码已通过测试。

手撕宽度至少 1180 时采用题面/编辑器/下方输出，小窗口切换题面与代码；同一编辑器保留文本与滚动。Practice 与 Interview 共用行号、Python 高亮、缩进、撤销重做和保存状态。动态手撕「运行代码」或 `Ctrl+R` / `Command+R` 先保存再执行，输出 stdout、错误、退出码与 revision，单次最多 30 秒。「公开测试」独立运行原有单测；自测退出码 0 不代表算法正确或测试通过。

点击「提交给面试官」锁定当前代码与该 revision 的运行、公开测试事实，直接结束问答并进入后台评分，不额外请求一次“是否还有下一问”。不要求完整实现或测试通过，不自动补代码。评分引文必须来自锁定的实际代码，不拿 JSON 转义文本比较。修改后未重跑的旧结果不作为新代码证据。旧会话保留原问题、Rubric 与协议；新体验请新开一场。

本轮建议沿「自我介绍 → 多角度经历 → 原理 → 手撕自测 → 结束评分 → 缺口练习」验收。模型的语义深度仍需人工判断，不把题数当成覆盖证据。浅/深主题实图：[代码区](images/unified-interview-20260908/coding-light.png) / [复盘](images/unified-interview-20260908/report-dark.png)；完整范围与真实传输失败见[本轮记录](../plans/active/unified-difficulty-interview-workbench.zh.md)。

测试输出只显示当前面试题的结果，不沿用刷题页输出。重新加载本场时恢复已保存的测试计数与 revision，完整输出可通过重新测试查看。口述回答未提交或代码未保存时，切换学习档案会被阻止；请返回面试处理草稿后再切换。**尚未提交的口述草稿不是持久化记录，关闭应用前请先提交并锁定回答。**

Codex 与普通 API 共用逐轮流程和本地结果校验。同场、同模型、同授权快照复用 Codex Thread，不逐轮重新检测连接；范围变化则隔离旧上下文。Codex 使用 `outputSchema`，DeepSeek 使用 JSON Output；正文流式预览，但完整校验后才冻结，不能回答半截问题。服务只返回思考、空正文或无效结构时保留原回答与原模型设置，可原位重试。

代码候选按岗位、环境与难度筛选：简单 1–2、标准 2–4、困难 3–5，困难优先更高等级；所有用户同条件同资格，不按实习/校招/年限限制。仍要求 ready、正式验证级别与真实运行资产。没有 PyTorch 也可开始非代码问答，没有可运行手撕时明确保留覆盖缺口，不能声称整场完整完成。

选择 Codex 后，面试设置中会显示模型与推理强度摘要，并提供“设置模型与推理强度”入口。“已发现”只证明找到程序，“已连接”只证明建立了 App Server 会话，都不保证当前模型兼容。模型要求新版 Codex 时，界面会提示选择新版可执行文件或兼容模型。请求期间可以点击“停止请求”；中断不会删除已锁定回答。模型请求最长等待 180 秒，超时后关闭该应用拥有的连接；下次重试会重新连接，原发送范围不变时不再确认。连接失败、格式无效和材料授权变化等错误显示在作答页，附排查编号，不只显示通用 Toast。

如果当前 AI 方式为 **No-AI**，模拟面试页会停留在明确的锁定说明，不会伪造面试 Session、评分或报告。你可以从该页面打开 AI 连接，或返回刷题训练；No-AI 刷题、公开测试、复盘和间隔复测始终可用。

### 面试 AI 连接

面试请求失败后，可在回答区点击「复制脱敏诊断」，直接取得本轮结束原因、响应计数、耗时与服务提供的用量/请求编号。不会复制材料、回答、思考正文或 Key，也不触发额外请求。已保存回答可原位重试，原模型与推理强度不自动改变；未知结束原因不再视为完成。详见[面试响应失败说明](ai-connections.md#常见错误)。当前仅源码提供，不代表已经修复所有真实服务空回复。

上下文预览列出将发送的每个部分。普通 Provider 只接收确认文本；Codex 使用官方 App Server 作为面试官，不修改候选人的代码。连接页的 Codex 按钮直接连接面试官，不再提供教练或仓库代理模式。详见 [AI 连接](ai-connections.md)。

经历环节先邀请候选人介绍一段与岗位相关的项目、实习、比赛或论文，再沿实际回答逐层追问；不知道或非本人负责时换角度取证。简历细节不等于已经口头讲过。简单、标准、困难调整语气与深广度，但评分宽容度不变，不辱骂或补造经历。

八岗位有各自的追问角度，面经来源与置信度见[研究记录](research/post_training_agent_interview_sources.md)。这些来源用于提炼考察方式，不代表公司统一标准或考频统计。背景决定切入点，不按学历或年限自动降低要求。

策略由 [`dynamic-interviewer.md`](../coach/prompts/dynamic-interviewer.md) 和 [`interview_flow.py`](../src/llm_interview_lab/interview_flow.py) 实际发送。新面试不设最低/最多轮数，简单/标准/困难目标分别为 2/3/3 个经历角度、3/3/4 个原理主题。覆盖记录关联真实问答和可核对引文，不保存未来计划。引文无法核实时该次覆盖不计数，但不阻塞合法下一问。

时间预算为自我介绍 5%、经历 40%、原理 25%、手撕 30%。阅读、思考、输入和录音计时，AI 生成/重试/结束评分不扣候选时间；暂停与 AI 等待重叠只扣除一次。覆盖充分可提前推进，时间不足则转场并记录缺口，不为凑题挤掉手撕。自动化验证不等于每个模型都能问得足够深入。

新协议若收到不在真实候选中的手撕 ID，会拒绝冻结并提示重试，不静默换题。题面、starter 和公开测试必须存在；无可运行题时保留缺失环节。历史协议原有纠正行为仅用于旧会话恢复。

设置会在后台检查 Codex 的 PATH、常见安装位置和已保存的可执行文件。状态分为“检查中 / 已发现 / 未发现”，发现时只显示脱敏来源；Finder 或 Explorer 没有继承完整 PATH 时，可用“选择 Codex”指定文件。Codex 不是本地训练或 No-AI 的前置条件。

AI 连接页优先显示当前档案的已保存连接。DeepSeek 等服务的 Key 保存一次后，关闭和重启应用仍可复用，不需要再次填写。点击「修改模型 / Key」可以调整模型或推理强度：Key 留空会保留原值，填写新 Key 则替换。点击「删除连接与 Key」并确认后，会同时删除连接配置与系统密钥环中的 Key，不删除档案或面试记录。界面不会回显密钥，也不会把密钥存成明文文件。

同一次运行中，添加材料或刷新同一档案不清空未改变配置的成功测试状态。启动或切换档案后，应用会在后台恢复上次选用的 AI：Codex 发现后自动连接，普通 API 使用已保存 Key 运行现有的短连接检测（服务可能计入少量用量，不含简历或回答）；No-AI 不连接。就绪状态只在实际检测成功后显示，失败可在 AI 连接页重试，不阻塞本地训练。恢复进行中的面试时可直接提交回答；就绪状态不是持续网络可用性的保证。

顶部左侧的侧栏按钮可展开或收起导航，记住上次状态；左下角档案装饰已移除，切换档案仍在设置中。宽屏面试区随窗口增宽，短问题与回答框自然相接，不再强行隔出大块空白。练习页默认展示完整中文接口、约束、验收与口述要求，而非列表摘要；可查看英文原题，题目源文件与公开测试契约不变。

材料组合、是否使用材料及相同 ID/源文件 SHA/提取文本 SHA 的选中状态会随本档案保存。下次准备自动恢复，并在摘要显示；撤销材料权限或文件内容改变后不复用旧选择授权。每场开始仍确认实际发送范围，不在启动或恢复设置时上传材料；远程录音授权仍逐次确认。

源码模式使用 `LLM_LAB_DESKTOP_DATA_ROOT` 时，每次启动都会同步当前源码的公开课程、面试提示和 Schema，不清空其中的 Profile、材料或答案。同版本源码新增提示文件后，旧 UAT 目录也会更新；若资源仍缺失，错误显示在「开始面试」旁，并说明重启同步的处理方式，不再只出现通用 Toast。

v1.0.0 可直接选择 **DeepSeek**，模型与推理强度位于表单首屏，地址无需手填；详见 [DeepSeek 接入与实测范围](ai-connections.md#deepseek当前源码)。历史高推理失败仍需如实区分，不因公开发布宣称解决。

非代码面试支持“语音输入 → 流式预览、停句自动校准 → 完成录音 → 编辑 → 提交”。当前源码默认使用 **Zipformer 预览 + Qwen3-ASR 0.6B 本地停句校准**，SenseVoice 保持移除。无需 API Key、PyTorch 或服务器；完整组合约 1.19 GB，旧流式模型的完整文件会复用。校准根据原音频执行，期间可以继续说话、手打；完成后只追加一次到草稿，不自动提交。首次校准加载较慢，识别仍可能有术语误写，须检查后提交。首次使用需在本机数据目录下载模型；示例 UAT 路径不表示其他用户已准备好权重。详见[本地流式语音输入](local-stt.md)。

本地录音不需要 API Key，也不会自动上传。没有麦克风、目录不可写或录音组件失败时，原因显示在录音按钮附近，可重试或继续输入文字。2026-09-07 在当前 Windows 的正式页面实际点击录音、停止，生成了约 5.57 秒、48 kHz、双声道的有效 WAV；使用隔离测试档案，未发送音频。这不是 macOS 或所有麦克风设备的实测结论。

录音中离开面试页、暂停、到时或退出会停止采音，保留音频并取消未开始的自动转录。已经开始的转录可以在切页后完成，仍追加到原题草稿，不会抢走设置页输入焦点；暂停后需恢复面试并手动重试。当前面试时钟的普通秒数变化只刷新面试区域，不再带动其他页面重算。

远程转录仍可选 OpenAI / OpenAI-compatible 的 `/audio/transcriptions`，使用独立的 `whisper-1` 模型，所选服务必须支持这个接口。DeepSeek 文字面试可以直接搭配本地转录，不需要再提供另一把 Key。转录方式会记住；只有远程方式需要每次新录音或换题后重新授权。音频不会从本地转录自动降级上传，转录失败也不删除音频。此轮未调用真实远程转录服务。

### Qt 启动告警

`Member palette ... overrides` 是页面自定义属性与 Qt 基类同名的告警，当前源码已将页面属性改为 `colors`，没有屏蔽日志。`DirectWrite ... MS Sans Serif` 是旧字体兼容告警，当前 Windows 仍可出现；`Retrying to obtain clipboard` 表示剪贴板暂时被占用后的重试。二者不等于 Codex/API 连接失败。本轮真实面试运行在字体告警存在时仍能接续问题；没有据此宣称所有字体环境已修复。

### 学习进度

自评、练习证据、岗位覆盖与待补技能分开显示，不展示按求职阶段换算的目标准备度，不是 Offer 概率或录用判断。

### 设置

主题、文字大小和界面语言排列为三行，当前选项有明确选中态。默认简体中文，English 为实验性选项。面试页和 AI 连接页的模型设置入口会直接滚动到 Codex 模型与推理强度控件，不用从设置页顶部查找。

模型名称和推理强度未保存时，不会被后台转录或其他页面状态刷新重置；修改后仍需点击原有保存按钮。

还可切换学习档案、打开数据与日志目录，以及选择或重新自动查找 Codex。Alpha.1 Windows 数据迁移必须由用户确认；应用先复制、计算 SHA-256、保留本地备份，再切换到新位置，绝不删除源目录。

## 界面历史截图（2026-09-05）

本轮借鉴 ChatGPT 的中性色、内容优先与清晰主操作，将面试设置和作答分为两个视图，不再并排展示两块大卡片。保留项目自己的图标、名称和业务流程；设计原则参考 [OpenAI UI 指南](https://developers.openai.com/plugins/concepts/ui-guidelines)，不是对官方客户端的逐像素复刻。

当时作答页以“本场信息”收纳岗位、难度与状态；提交操作固定在底部。长题目和授权材料按内容高度排布并可滚动。下方 AI 辅助截图属于已删除页面的历史证据，不是当前入口。

以下为当时正式 QML 页面在 Windows 上的自动交互截图，使用隔离测试档案与合成回答，不是演示 Controller，也不包含真实求职材料。确认弹窗场景使用 **Fake Codex**；其连接标记不证明真实账户可用。截图对应的源码提交、窗口大小和 SHA-256 见 [截图清单](images/chatgpt-ui-20260905/manifest.json)。它们保留视觉迭代历史；当前动态面试已经改为上文的一次提交流程，**不是新的桌面 Release**。

| 页面 | 截图 |
|---|---|
| 面试作答 · 1280×800 · 100% 字号 | [浅色](images/chatgpt-ui-20260905/interview-light.png) · [深色](images/chatgpt-ui-20260905/interview-dark.png) |
| 上下文确认 · 1280×800 · 125% 字号 | [深色；Fake Codex 交互验证](images/chatgpt-ui-20260905/context-dark.png) |
| 首页 · 900×620 · 125% 字号 | [浅色；下方内容可滚动](images/chatgpt-ui-20260905/home-small-light.png) |
| AI 辅助 · 900×620 · 125% 字号 | [浅色；中文输入](images/chatgpt-ui-20260905/coach-small-light.png) |

## 快捷键

| 操作 | Windows / Linux | macOS |
|---|---|---|
| 设置 | 系统菜单 | `Command + ,` |
| 运行公开测试（刷题或面试手撕） | `Ctrl + R` | `Command + R` |
| 答题页主安全动作（运行测试） | `Ctrl + Enter` | `Command + Enter` |
| 退出 | `Alt + F4` | `Command + Q` |


提交、审批和覆盖类操作不会绑定容易误触的全局快捷键。

## 数据位置

- 源码 / CLI：仓库内 `workspace/`；
- 隔离验收：`LLM_LAB_DESKTOP_DATA_ROOT` 可指定独立目录，源码模式从当前安装的源码位置补齐公共资产，不复制真实学习档案；
- 打包桌面：Qt `QStandardPaths.AppDataLocation`；
- Windows 与 macOS 均不会把真实数据写入 EXE、`.app/Contents/` 或安装目录；
- 设置页会显示并打开实际目录。

日志使用小型滚动文件，默认不上传，不记录 API Key、Authorization Header、完整材料、完整答案、Oracle、Private Tests 或其他学习档案。

## 无 AI 模式

以下故障都不应阻止本地训练：断网、缺少或错误 Key、429 / 500、Ollama 未启动、Codex 未安装或未登录、Keyring 不可用。界面会给出中文下一步，并保留 No-AI 入口。

## 源码运行

无需编译 exe 或 `.app`。首次是“安装 Python → 获取代码 → 准备项目环境 → 启动”，之后只需最后一步。推荐 **Python 3.11**：项目最低要求为 3.10，但部分 AI 适配依赖只在 3.11+ 安装。不要因为机器上有 `python` 命令就假定版本正确。

### 先获取代码并找到根目录

新机器需要 Git；首次安装依赖需要联网。打开终端执行：

```bash
git --version
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
```

已有仓库不必重复克隆，进入原目录即可。下面所有命令都从包含 `pyproject.toml`、`src` 和 `scripts/run_desktop.py` 的目录执行。macOS / Linux 可用 `pwd`、Windows PowerShell 可用 `Get-Location` 确认当前位置。复制命令时不要带上用户名、目录前缀或终端的 `%` / `$` 提示符。

### Windows

先确认解释器：

```powershell
py -3.11 --version
```

应显示 `Python 3.11.x`。没有 `py` 或没有该版本时，先通过 Python 官方发行渠道安装 Python 3.11，并重新打开 PowerShell。若只有 `python` 命令，先执行 `python --version` 核实版本；只有确认是合适的 Python 3 后才用它替换下面的 `py -3.11`。

首次准备（新机器或依赖变化时执行一次）：

```powershell
py -3.11 scripts/run_desktop.py --setup
```

以后启动（已有本项目 `.venv` 可直接用）：

```powershell
.\.venv\Scripts\python.exe scripts/run_desktop.py
```

不需要 `Activate.ps1`、更改 PowerShell 执行策略或设置 `PYTHONPATH`。首次准备失败时先处理安装错误，不要直接跳到启动命令。

### macOS：先准备 Python，再启动

这些步骤用于源码，不是 DMG 安装。尤其不要复制另一台机器的 `.venv`，Windows 的虚拟环境不能拿到 Mac 使用。

**1. 检查现有 Python。**

```bash
command -v python3.11
python3.11 --version
```

能显示 `Python 3.11.x`，就跳到第 3 步。找不到命令，表示没有安装这个版本或它不在 PATH 中；不要改用未经核实的 `python`，它可能指向旧解释器。

**2. 缺少 Python 3.11 时安装。**

已有 Homebrew 时：

```bash
brew --version
brew install python@3.11
"$(brew --prefix python@3.11)/bin/python3.11" --version
```

安装命令及版本命令见 [Homebrew Python 3.11 官方页面](https://formulae.brew.sh/formula/python@3.11)。没有 `brew` 时，先按 [Homebrew 官网](https://brew.sh/)安装，阅读并完成安装结束时的 PATH 配置提示，然后重新打开终端。公司设备如有安装限制，请使用获准的安装方式，不绕过管理策略。

下面使用 Homebrew 返回的安装路径，不依赖 `python` 别名，也不用自己猜 `/opt/homebrew` 或 `/usr/local`。

**3. 在仓库根目录准备环境。两种方式选一种。**

已有可用的 `python3.11`：

```bash
python3.11 scripts/run_desktop.py --setup
```

通过 Homebrew 安装、但 `python3.11` 仍不在 PATH 中：

```bash
"$(brew --prefix python@3.11)/bin/python3.11" scripts/run_desktop.py --setup
```

等命令成功结束、回到终端提示符后再继续；下载依赖需要时间。若出现 `ERROR` 或安装失败，先处理该错误。此时不会自动弹出应用窗口。

**4. 检查项目环境并启动。**

```bash
.venv/bin/python --version
.venv/bin/python scripts/run_desktop.py
```

以后通常只需第二条。启动时保留终端窗口，出错时可查看提示。macOS 首次录音可能需要在“系统设置 → 隐私与安全性 → 麦克风”中授权实际承载启动的终端或 IDE；权限问题与 Python 环境安装问题分开处理。

### Linux

需要可用的图形桌面，以及 Python 3.11 的 pip / venv 支持；具体安装命令由发行版决定。先核实 `python3.11 --version`，再执行：

```bash
python3.11 scripts/run_desktop.py --setup
.venv/bin/python scripts/run_desktop.py
```

### `--setup` 到底做什么？

它使用执行脚本的 Python 创建缺失的 `.venv`，再向该环境安装 `.[desktop,ai,dev]` 可编辑依赖；不安装系统 Python、不启动应用、不打包、不下载语音权重。

如果 `.venv` 已存在，它会复用该环境，**不会因为你改用 Python 3.11 执行 `--setup` 就自动升级旧虚拟环境的 Python**。检查 `.venv` 自身的 `--version` 才能确定应用实际使用哪个版本。

初始化与启动是两个步骤：`.venv/bin/python`（Windows 为 `.venv\Scripts\python.exe`）不存在时，说明环境还没创建成功；即便它存在，也需确认依赖安装成功。正常启动不会重复运行 pip。

### 拉取新版与保留数据

先关闭应用，在仓库根目录检查：

```bash
git status --short
git branch --show-current
```

若有自己的源码或文档改动，先保存并按自己的 Git 工作流处理；不要用 `reset --hard`、强制切换或删除工作区来更新。确认可以切到 main 后：

```bash
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

如果提示不能快进或存在冲突，停止并处理分支差异，不强推或覆盖本地修改。通过 ZIP 下载的源码不带 Git 历史，不能直接 `git pull`；需要更新前先保留自己的数据和改动。

只改 Python / QML 时重新启动即可。依赖声明变更或维护者明确要求时，在已确认版本正确的 `.venv` 内重新准备：

```powershell
# Windows
.\.venv\Scripts\python.exe scripts/run_desktop.py --setup
```

```bash
# macOS / Linux
.venv/bin/python scripts/run_desktop.py --setup
```

### 日常修改与数据

- **改 Python / QML：** 保存文件，关闭应用，再运行上述启动命令；不需要编译或重新安装依赖，不提供热重载。
- **改依赖：** 再执行一次 `--setup`；普通启动不会运行 pip，也不会自动拉取 Git 或覆盖代码。
- **测试数据：** 未指定覆盖时固定使用 `workspace/maintainer/manual-uat`，与此前手动 UAT 命令一致；重启继续使用，不自动清空。首次新目录需自己创建档案，不生成演示档案。
- **换数据目录：** 启动命令后追加 `--data-root "绝对路径"`；已有 `LLM_LAB_DESKTOP_DATA_ROOT` 仍受尊重，显式参数优先。目录隔离不等于隔离系统密钥环，API Key 仍由系统管理。
- **PyTorch 题：** 按需用 `.venv` 的 Python 执行 `-m pip install -e ".[torch,dev]"`；默认不强制安装 PyTorch。
- **语音：** 在应用内下载本地权重后使用；正常启动不反复下载。

脚本始终从当前仓库 `src` 加载代码，避免旧 Worktree 的可编辑安装影响测试。原来的 `python -m llm_interview_lab.desktop.main` 与环境变量启动方式仍可使用。不要用 `--smoke-test` 或 `--screenshot` 做人工验收，它们使用合成状态。

例如，希望在独立目录验收，不影响原档案：

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/run_desktop.py --data-root "E:\InterviewLabData\manual-check"
```

```bash
# macOS / Linux：请替换成你自己拥有且可写的绝对路径
.venv/bin/python scripts/run_desktop.py --data-root "/Users/你的用户名/InterviewLabData/manual-check"
```

换目录后看不到旧档案通常是数据位置不同，不表示旧数据被删除。源码默认目录与已安装 `.app` / exe 的数据目录可能不同；实际位置在设置页核对。不要为修启动问题删除 `workspace`、材料目录或系统密钥环。

### 常见启动报错

| 提示或现象 | 含义与处理 |
|---|---|
| `python3.11: command not found` | 系统找不到指定解释器；先安装或使用上面的 Homebrew 完整路径，项目脚本不能替你安装系统 Python。 |
| `python scripts/run_desktop.py` 在类型标注处 `SyntaxError` | 解释器不支持脚本语法；先查看 `python --version`，再使用确认过的 Python 3.11。不要删脚本类型标注来兼容旧 Python。 |
| `.venv/bin/python: no such file or directory` | 先确认在正确仓库根目录；再检查 `--setup` 是否真正成功。新克隆的仓库不会包含 `.venv`。 |
| `can't open file ... scripts/run_desktop.py` | 通常是目录不对或源码不完整；进入包含 `pyproject.toml` 的目录。 |
| 安装出现证书、网络超时或包下载失败 | 这是依赖准备失败，不是面试 API 故障。保留首个明确错误，检查网络/获准的代理及证书配置；不要关闭证书校验或反复尝试启动半安装环境。 |
| 找不到 `PySide6` / `httpx` 等模块 | 检查是否使用本仓库 `.venv`，并用它重新执行 `--setup`；不要把依赖装到另一个全局 Python。 |
| `.venv` 的 Python 版本不对或环境来自另一台机器 | 先关闭应用，核实当前仓库位置，仅将本仓库 `.venv` 重命名备份，再用 Python 3.11 重新 `--setup`；不要动 `workspace`。脚本不会自动迁移已有环境。 |
| 程序打开但 AI 连接失败 | 已越过源码启动阶段。去“AI 连接”检查配置并复制脱敏诊断，不要通过重装 Python 代替 API 排查。 |

反馈时附操作系统/芯片、当前提交（`git log -1 --oneline`）、执行命令、Python 版本及首个错误片段即可。终端截图先遮住用户名、个人路径、API Key 和简历内容；不要发送整个数据目录。

2026-09-09 已在 Windows 上用上述脚本正常启动（仅指定独立数据目录和窗口尺寸，未使用演示模式）：通过系统无障碍接口输入中文名称、选择岗位、点击开始训练，成功打开真实 `ATT-022` 题面与代码编辑器，随后正常关闭，退出码为 0。此检查未调用付费 AI、未运行题目测试，不代表 macOS 实机验收。

### 源码新增：连接诊断与应用内更新

AI 连接失败时，字段附近显示错误阶段、编号与下一步；点击「复制脱敏诊断」即可反馈维护者，不需要发送 Key、整个日志或个人材料。401、证书、DNS、代理、超时与本地密钥环故障分别处理。

「设置 → 应用更新 → 检查更新 → 下载增量更新 → 安装并重启」已加入源码，**但尚未打包验证或发布**。以后恢复发布时，旧 v1.0.0 才需一次性安装过渡包；不要求现在下载新包。新更新器复用未变化文件/数据块，只下载变化块或小文件组，实际下载量取决于改动。

请先结束录音/面试；确认后保存当前草稿，退出再替换程序。下载及校验失败保持当前版本，启动失败保留或恢复旧程序。档案、Key、材料、答案和本地语音权重不搬动。程序目录必须可写，mac 应用不能直接在只读 DMG 中更新。**源码模式不会自动覆盖 Git 工作区**；具体限制及验证范围见[预发布说明](release-notes-v1.0.1-alpha.1.md)。

离屏 Smoke：

```bash
llm-lab-gui --smoke-test
llm-lab-gui --screenshot desktop-home.png --screenshot-page home
```

## 开发与打包

Windows 使用：

```powershell
python scripts/build_windows_desktop.py --output dist/release
python scripts/check_desktop_artifact.py dist/release/LLMInterviewLab/LLMInterviewLab.exe --report dist/release/desktop-nuitka-report.xml --archive dist/release/LLMInterviewLab-Windows-x64-portable.zip
```

macOS Apple Silicon 使用：

```bash
python scripts/build_macos_desktop.py
python scripts/check_macos_artifact.py \
  dist/release-macos/LLMInterviewLab-macOS-arm64.app.zip \
  dist/release-macos/LLMInterviewLab-macOS-arm64.dmg
```

GUI 依赖是可选依赖，不会拖入核心 CLI 测试矩阵。CI 使用离屏 QML Smoke、Fake Provider、Fake Codex 和 Mock Keyring，不访问真实账户。

## 排错

- **窗口无法启动：** 先运行 `llm-lab-gui --smoke-test`，再从设置打开日志目录；源码用户运行 `python -m pip install -e ".[desktop,ai,dev]"`。
- **Windows 双击无窗口：** 查看原生错误框中的错误编号和
  `%LOCALAPPDATA%\LLMInterviewLab\logs\bootstrap.log`；确保解压了完整目录，而不是只复制 EXE。
- **Ollama 连接失败：** 确认 Ollama 已启动，地址通常为 `http://127.0.0.1:11434`，然后重新测试。
- **Codex 未检测到：** macOS Finder 不一定继承 Shell PATH；从设置选择 Codex 可执行文件。
- **密钥环不可用：** 应用不会写明文 Key。继续使用 No-AI，并先修复系统 Keychain / Credential Manager。
- **PyTorch 题缺少依赖：** 源码安装执行 `python -m pip install -e ".[torch,dev]"`。

本地 Grader 只用于运行你本人信任的代码，不是恶意代码安全沙箱。

## Phase 2 视觉与验证证据

当前正式页面的合成截图（不含真实档案、答案、材料或密钥）位于 [`docs/images/phase2/`](../docs/images/phase2/)，由该目录中的 `manifest.json` 记录页面、尺寸、主题和 SHA-256。它们用于核对首用入口、首页、首题、面试页面和设置布局；截图不会替代真实 Profile 或跨平台实机验收。
