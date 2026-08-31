# LLM Interview Lab 产品与开发总 Plan v1.0

> 状态：产品决策已冻结，尚未转换为 Codex 执行 Prompt
> 目标：在不浪费时间、不重复造轮子、不以“写了很多代码”冒充产品完成度的前提下，把现有 Alpha 迭代为高质量、本地优先、可个性化、可语音交互的 AI 面试训练工作台。
> 建议落盘位置：`plans/active/product-v1-dynamic-interview-workbench.md`

---

## 0. 文档控制

### 0.1 当前代码基线

后续开发不得从旧 `main` 的认知重新开始，而应以以下检查点为基础：

- 仓库：`ComistryMo/llm_interview_lab`
- 已完成分支：`feature/real-user-iteration-20260831`
- 已确认远端 HEAD：`fa0c10afb605ccbbd7143f8bac977392dccb03d8`
- 当前分支相对 `main@36db5ac3ba21580323a5116e356830badabcc0f4`：包含现有真实用户迭代工作
- 当前分支尚未合并 `main`、未创建 Tag、未发布 Release
- 当前报告裁决：`PARTIAL`

### 0.2 已有验证证据

现有分支报告记录：

- 唯一一次本地全量回归：`507 passed, 14 skipped`
- 材料测试：`25 passed, 3 skipped`
- 个性化计划定向测试：`5 passed, 30 deselected`
- 语音、转录、面试组合测试：`40 passed`
- 最新受影响定向测试：`9 passed, 24 deselected`
- 相关模块 `py_compile` 与 `git diff --check` 通过
- 尚未执行新的 RC CI
- 尚缺 Windows standalone Explorer 双击实机验收
- 尚缺 macOS 构建、运行和 Keychain 实机验收
- 尚缺真实麦克风与真实远程 Provider 的完整平台验收

这些结果是后续开发的**基线证据**，不是最终发布证据。后续大量修改后，不得继续把这次 `507 passed` 当作最终版本通过。

### 0.3 上下文边界

现有分支中的 PDF/DOCX、个性化计划和语音 MVP，是在本轮产品讨论开始前已经启动的工作。它们不能被误认为已经实现了本 Plan 中后来冻结的产品形态。

尤其是：

- 现有实现会在面试前生成并冻结个性化计划；
- 本 Plan 要求严格模拟面试只初始化覆盖状态，并按轮动态生成当前问题；
- 现有语音路径以 OpenAI-compatible 远程转录为主；
- 本 Plan 要求本地 STT 为默认，远程 STT 只能作为用户主动配置的高级选项；
- 现有转录进入可编辑草稿；
- 本 Plan 要求训练模式可编辑，严格模拟模式保存不可覆盖的原始 Transcript；
- 现有个性化 Golden Path 仅覆盖 `post_training_engineer + new_grad + medium`；
- 本 Plan 要求最终覆盖所有公开岗位及其岗位差异。

---

# 1. 现有实现与目标产品的衔接裁决

## 1.1 可以直接保留并扩展

| 现有能力 | 裁决 | 后续动作 |
|---|---|---|
| PDF 文本提取 | 保留 | 增加提取质量、预览、独立发送授权与错误状态 |
| DOCX 段落和表格提取 | 保留 | 增加预览、提取质量、原文件发送能力 |
| 原文件 SHA-256 与文本快照绑定 | 保留 | 作为逐场授权失效判断的事实源 |
| 材料逐场授权基础 | 保留 | 拆分“发送提取文本”和“发送原文件”两项授权 |
| Context Preview | 保留 | 从“预览未来计划”改为“预览本场设置、材料和发送范围” |
| Provider 严格 JSON 解码基础 | 保留 | 改造成每轮 `NextTurn`、评分和报告的运行时协议校验 |
| Coding 题由本地验证题库决定 | 保留 | 接入统一编程工作台和新的题目排除/复测规则 |
| Qt Multimedia 本地录音 | 保留 | 纳入本地语音状态机、权限和设备异常恢复 |
| OpenAI-compatible 转录适配器 | 降级为可选 | 不作为默认 STT，只作为用户主动配置的远程 STT |
| Connection `ready` 布尔状态 | 保留 | 所有 QML 继续只读结构化状态，不解析显示文案 |
| Profile/问题/异步操作身份隔离 | 保留 | 扩展到动态 Turn、STT、TTS、Grader 和 Provider Retry |
| 材料字段空值安全读取 | 保留 | 继续补齐 QML ViewModel，而不是页面解析原始字典 |

## 1.2 必须重构而不能按现状继续扩展

| 现有能力 | 当前问题 | 目标 |
|---|---|---|
| 个性化面试计划 | 面试前生成问题位置和计划并冻结 | 只冻结设置、材料、覆盖合同；每轮只生成当前问题 |
| 岗位蓝图 | 面向固定轮次和固定内容 | 改为隐藏的 `Interview Coverage Contract` |
| Session 中问题列表 | 容易预存未来题 | 新 Session 只保存已实际提出的 Turn |
| 计划确认 UI | 可能向用户泄露未来内容 | 严格模拟只确认材料和设置；训练模式可展示宽泛方向 |
| 可编辑转录草稿 | 不区分训练和严格模拟 | 训练可编辑；严格模拟保存不可覆盖原始 Transcript |
| 单一岗位 Golden Path | 仅一个岗位/阶段/难度 | 扩展到全部公开岗位，岗位决定 Coding 和评分维度 |
| Voice MVP | 远程 STT 为主要完成路径 | 本地 STT 默认、远程 STT 可选、本地 TTS 可选 |

## 1.3 尚未实现，必须新增

- 统一编程题工作台
- 官方答案与官方讲解
- 官方答案解锁和 Assisted 证据规则
- 高质量视觉系统重设计
- 三套高保真方向稿
- 动态逐轮面试引擎
- 训练面试与严格模拟面试双模式
- 上次材料组合复用
- 原始 PDF/DOCX 与提取文本的独立授权
- 本地 STT 模型包
- 本地 TTS 模型包
- 男声/女声、正式/自然风格与试听
- 不完整面试的部分证据报告
- 证据可跳转的面试报告
- 原始 Transcript 与复盘副本
- Markdown/JSON/录音/代码证据导出
- 面试、Transcript、音频、报告和 Profile 的细粒度删除
- 真正的 Windows/macOS 发布级实机验收

---

# 2. 产品目标

## 2.1 最终定位

LLM Interview Lab 是一个：

> 本地优先、岗位感知、材料驱动、动态追问、可语音交互、Coding 结果由确定性 Grader 负责的 AI 面试训练工作台。

## 2.2 两条核心主线

### No-AI：确定性训练

提供：

- 固定课程和知识库
- 中文题面
- 统一编程工作台
- 可见样例运行
- 正式验证
- 官方答案
- 本地提交记录
- Review
- D+2 / D+7
- 进度和证据

### AI：个性化面试

提供：

- 简历、项目、论文、比赛、JD 驱动的提问
- 根据本场前序回答动态追问
- 基于知识库的八股候选与事实约束
- 岗位相关的场景题和行为题
- 本地验证题库中的 Coding Round
- 严格模拟面试
- 训练面试
- 结构化评分和证据报告
- 本地优先语音交互

## 2.3 明确非目标

首个完整版本不做：

- 全双工实时语音通话、抢话和复杂 VAD
- 付费或远程 TTS API
- 连接阶段的模型能力考试、白名单或模型分级
- 严格模拟面试的未来问题清单
- AI 临时生成、未经验证的正式 Coding 题
- Web UI、账号、云同步、在线排行榜
- 没有真实后端的“讨论”功能
- 默认上传 Transcript、代码、音频或材料
- Offer 概率
- 大面积玻璃背景、霓虹发光和廉价渐变
- 首版自定义无边框窗口
- 首版强制引入 Monaco/QWebEngine
- 首版扫描 PDF OCR；文本型 PDF/DOCX 先稳定完成

---

# 3. 已冻结产品决策

## 3.1 AI Provider

- 用户可自由接入 DeepSeek、Codex、GLM、Kimi K3、OpenAI、OpenAI-compatible、Anthropic、Gemini、Ollama 等。
- Codex App Server 可作为整场正式面试官，不只做 Coding Review。
- 不做 `Interview Readiness Check`。
- 不提供“基础模型/完整模型”两档。
- 连接成功后即可用于面试。
- 每轮仍进行运行时 Schema 校验；异常时自动修复一次，仍失败则暂停。
- Provider 在 UI 中平级展示，但能力字段必须真实反映是否支持：
  - 普通文本
  - 流式输出
  - 原始文件
  - Usage
  - 取消/重试
  - Codex Approval

## 3.2 No-AI 面试入口

- 模拟面试入口保留但锁定。
- 点击后解释需要 AI，并引导：
  - 连接普通 LLM
  - 配置本地 Ollama
  - 连接 Codex
- No-AI 不创建假的面试 Session、评分或报告。

## 3.3 面试模式

### 训练面试 `guided_training`

允许：

- 查看宽泛训练方向
- 查看为什么追问
- 查看本轮反馈
- 使用提示
- 重答一次
- 修正 Transcript
- 查看关联知识点

### 严格模拟 `strict_mock`

要求：

- 不显示未来问题和内部计划
- 一问一答
- 不提供提示和即时评分
- 回答提交后不可修改
- Coding 锁定前不能提供解法
- 只在结束后统一复盘
- 时间和证据规则严格

## 3.4 动态面试

- 面试开始时不预生成问题列表。
- 只初始化设置、材料授权、覆盖合同和上下文。
- 第一问即时生成。
- 后续每一问必须结合：
  - 用户背景
  - 授权材料
  - 当前问题
  - 当前回答
  - 本场全部前置对话
  - 已覆盖能力
  - 未解决疑点
  - 本地训练摘要
  - 剩余时间
  - 岗位和难度
- Session 不保存未来问题，只保存已经真正问过的问题。
- 切换主题必须自然衔接，不能随机跳转。

## 3.5 面试设置

首屏只显示：

- 目标岗位
- 求职阶段
- 时长
- 难度
- AI 模型
- 材料
- 训练/模拟模式
- 语音开关
- 开始

高级设置包含：

- 重点方向
- 是否包含 Coding
- 面试官风格
- 压力程度
- 问题语言
- 回答方式
- 是否保留录音
- 最大 Token 预算

## 3.6 材料

导入：

- PDF 本地提取文本
- DOCX 本地提取段落和表格
- 展示提取预览
- 保存原文件 SHA
- 保存提取文本 SHA
- 源文件变化后旧授权失效

逐场授权拆成：

- 发送本地提取文本
- 同时发送原始文件

增加：

- “使用上一次材料组合”
- “默认预选上次使用的材料”

但：

> 自动预选不等于自动发送，用户每场仍需确认。

## 3.7 编程工作台

普通刷题左侧：

- 题目描述
- 知识解析
- 官方题解
- 提交记录

模拟面试左侧：

- 题目描述
- 本轮记录

右上：

- 代码编辑器

右下：

- 测试用例
- 执行结果
- AI 解析（满足显示条件时）

运行语义：

### 运行当前样例

- 只运行当前可见 Case
- 快速反馈
- 不形成正式证据
- 修改代码后旧结果 Stale

### 正式验证/提交

- 保存代码
- 运行完整确定性测试
- 绑定 Submission SHA
- 写入提交记录
- 形成 Review 客观证据
- 一次通过不等于 Mastered

面试中：

- 只公开 1–2 个样例 Case
- 完整测试在正式提交时运行
- AI 解析在代码锁定后才可用

## 3.8 官方答案

- 正式官方答案公开存放在仓库。
- 每道支持题可包含：
  - `official_solution.py`
  - `official_explanation.md`
- 必须通过正式测试并人工 Review。
- 首批覆盖：
  - 三条 Golden Quest
  - 综合关卡
  - 高频岗位 Coding 题
- 解锁条件：
  - 正式验证通过；或
  - 用户明确“放弃独立作答并查看题解”
- 查看后当前 Attempt 标记为 Assisted，不能直接形成独立 Mastery。
- 需要完成新的无帮助变式。
- 严格模拟面试不能把已经查看过官方完整答案的原题作为正式评分题。

题目规则：

- 最近做过：允许再次考
- 已 Mastered：允许作为复测评分题
- 最近面试出现过：允许再次出现，但报告标注重复暴露
- 看过官方答案：严格模拟中排除原题

## 3.9 语音

第一版采用轮次式：

```text
AI 提问
→ 本地 TTS 可选朗读
→ 用户录音
→ STT
→ 提交
→ 下一问
```

STT：

- 本地模型为默认
- 远程 STT 只作为高级可选
- 远程音频发送必须独立授权

TTS：

- 只允许系统本地语音或本地模型
- 不调用付费 TTS API
- 模型按需下载
- 至少提供正式自然男声、正式自然女声
- 可扩展自然亲切风格
- 可试听、调语速、重播、关闭自动播放
- TTS 失败立即降级为文字，不阻塞面试

Transcript：

- 训练模式：可编辑后提交
- 严格模拟：保存不可覆盖原始 Transcript
- 面试结束后可生成可编辑复盘副本
- 修正副本不改变评分依据

音频：

- 默认本地转录成功后删除
- 用户可主动选择本地保留
- 不默认上传

## 3.10 面试官风格

可选：

- 专业中性
- 严格追问
- 压力面试
- 自然友好

风格只影响措辞、追问强度、节奏和 TTS，不改变评分标准、岗位覆盖和 Coding 测试。

## 3.11 报告与评分

评分：

- 总体分：0–100
- 维度分：1–5
- 公共维度 + 岗位维度
- 总体分由固定权重计算，不让 AI随意生成
- 不完整/证据不足时不显示完整总体分
- 不提供 Offer 概率

公共维度：

- 回答正确性
- 理解深度
- 分析与推理
- 表达结构
- 证据与真实性
- 沟通质量

岗位维度按岗位增加：

- Coding
- 系统设计
- 实验设计
- 产品判断
- 工程可靠性
- 性能优化
- 数据与评测
- 项目贡献

每个重要结论必须关联：

- Turn ID
- 用户回答片段
- 代码 Revision
- Grader 结果
- 材料引用
- 推断与置信度

报告显示：

- 授权了哪些材料
- 问题基于哪些材料
- 发送的是提取文本还是原文件
- 未覆盖能力
- 评分置信度
- 最关键改进建议

## 3.12 数据与隐私

Transcript：

- 原始证据版本不可覆盖
- 复盘副本可编辑

导出：

- Markdown
- JSON
- 可选本地录音
- 代码与测试证据
- 材料引用清单
- SHA-256 Manifest

删除：

- 单场面试
- Transcript
- 原始录音
- 复盘副本
- AI 报告
- 材料
- Profile

上传：

- 默认绝不上传用户数据用于改进
- 用户可主动导出、预览、脱敏并提交反馈

---

# 4. 信息架构

建议最终主导航：

1. 首页
2. 刷题训练
3. 答题工作台
4. 模拟面试
5. AI 教练
6. 求职材料
7. 学习证据
8. AI 连接
9. 设置

## 4.1 首页

只突出一个主要下一步：

优先级：

```text
到期 D+2/D+7
> 待 Review
> 进行中题目
> 可恢复面试
> 岗位推荐题
> 开始模拟面试
```

最多两个次动作。

## 4.2 模拟面试入口状态

- No-AI：锁定说明页
- 有连接、无材料：可开始通用岗位面试
- 有材料：可开始个性化面试
- 有上次材料：显示“使用上次材料组合”
- 有未完成 Session：优先恢复
- Provider/音频异常：显示暂停与恢复操作

---

# 5. 动态面试状态机

```text
DRAFT
  ↓
CONSENT_REVIEW
  ↓
INITIALIZING
  ↓
GENERATING_CURRENT_QUESTION
  ↓
ASKING
  ↓
ANSWERING
  ↓
ANSWER_SUBMITTED
  ↓
ANALYZING
  ↓
GENERATING_NEXT
  ├── ASKING
  ├── CODING
  ├── CLOSING
  └── PAUSED
CODING
  ↓
ANALYZING
  ↓
CLOSING
  ↓
REPORTING
  ↓
COMPLETED / INCOMPLETE / TIMED_OUT
```

任意执行态可以进入：

```text
PAUSED
```

暂停原因包括：

- Provider 失败
- STT 失败
- 麦克风异常
- Grader 内部错误
- 应用恢复
- 用户主动暂停

## 5.1 恢复规则

- 问题已展示、答案未提交：恢复同一问题，不重新生成。
- 答案已提交、下一问未生成：从已完成 Turn 和 Coverage State 继续。
- 下一问只生成了部分文本：丢弃半截输出，记录 Retry，不作为正式问题。
- Coding 已提交：恢复 Submission SHA 和 Grader 证据。
- 报告生成失败：从冻结 Evidence 重试，不重新评分已完成 Turn。

---

# 6. 目标数据模型

## 6.1 InterviewSession v2

```yaml
schema_version: 2
interview_id: ...
profile_id: ...
mode: guided_training | strict_mock
status: ...
settings_snapshot: ...
provider_snapshot: ...
material_consent_snapshot: ...
training_summary_snapshot: ...
coverage_contract: ...
coverage_state: ...
current_turn_id: ...
completed_turn_ids: [...]
coding_state: ...
pause_state: ...
remaining_seconds: ...
context_summary: ...
report_ref: ...
```

严格要求：

- 不保存未来问题文本
- 不保存未经用户授权的材料正文
- 不把 AI 推断写成用户事实
- Old Session 保持可读

## 6.2 InterviewTurn

```yaml
turn_id: ...
round_type: ...
question_text: ...
question_generated_at: ...
question_context_hash: ...
transition_reason_internal: ...
candidate_answer:
  modality: text | voice | coding
  raw_text: ...
  raw_transcript: ...
  review_copy: ...
  audio_ref: ...
assessment:
  source: ai | grader | human
  dimensions: ...
  evidence_refs: ...
  confidence: ...
completed_at: ...
```

## 6.3 NextTurnResponse

Provider 每轮返回：

```yaml
action: ask | follow_up | switch_domain | start_coding | close
round_type: ...
question: ...
coverage_updates: ...
unresolved_points: ...
difficulty_adjustment: ...
transition_reason: ...
```

应用必须校验：

- 一次只有一个主问题
- `action` 合法
- 不引用不存在的材料
- 不预写未来问题
- Coding 只能引用本地已经选择并冻结的题目
- Strict Mock 中不能泄露答案和评分

第一次格式异常：

- 自动请求一次格式修复

仍异常：

- 暂停
- 保留状态
- 允许重试、切换 Provider 或结束为 incomplete

## 6.4 Context Compaction

长面试：

- 保留最近若干轮完整对话
- 更早 Turn 压缩为结构化摘要
- 摘要必须保留：
  - 用户原始事实
  - 已问问题
  - 关键回答
  - 未解决疑点
  - 已覆盖技能
  - Turn ID
- AI 推断必须单独存放，不能混入用户事实

---

# 7. 目标后端结构

保持模块化单体，不引入微服务或数据库。

```text
application/
  practice_service.py
  coding_workbench_service.py
  interview_service.py
  material_service.py
  voice_service.py
  report_service.py

interview/
  coverage_contract.py
  orchestrator.py
  turn_protocol.py
  context_compactor.py
  scoring.py
  report_builder.py
  coding_selector.py

ai/
  interview_provider.py
  chat_provider_adapter.py
  codex_provider_adapter.py
  transcription/
    local_stt.py
    remote_stt.py
  tts/
    local_tts.py

desktop/
  viewmodels/
    shell.py
    practice.py
    workbench.py
    interview.py
    materials.py
    connections.py
    voice.py
```

## 7.1 统一 Provider 接口

```python
class InterviewProvider:
    start_session(...)
    generate_next_turn(...)
    assess_turn(...)
    generate_report(...)
    cancel(...)
    retry(...)
```

Codex 和普通 API 只在 Adapter 层不同。

## 7.2 QML 边界

QML 只读取结构化字段：

- `state`
- `can_start`
- `can_submit`
- `status_label`
- `error_code`
- `error_message`
- `next_action`

禁止：

- 解析“已连接”等显示文案判断状态
- 在 QML 中决定题目是否可运行
- 在 QML 中计算面试是否完整
- 在 QML 中决定评分来源和业务状态

---

# 8. 视觉与交互 Plan

## 8.1 视觉决策门

开发完整页面前，先使用同一份真实编程题内容制作三套高保真方向：

1. Graphite Blue
2. Obsidian Violet
3. Warm Frost

每套必须同时展示：

- 深色
- 浅色
- 1280×800
- 关键悬浮、选中、焦点和运行状态

选定方向后才建立最终 Token。

## 8.2 视觉原则

- 平衡密度
- 克制磨砂
- 高级生产力工具感
- 代码、题面和长文本保持实色
- 默认跟随系统
- 深浅主题分别设计
- 不依赖过大圆角、发光边框或高饱和渐变制造“高级感”
- 保留系统原生窗口边框

## 8.3 磨砂范围

允许：

- 导航
- 顶部工具栏
- Command Palette
- Dialog
- Toast
- 浮动状态
- 计时和录音状态

禁止用于：

- 代码正文
- 题面正文
- 测试输出
- Traceback
- 官方题解
- Transcript 主体

## 8.4 统一编程工作台布局

```text
┌──────────────────────┬──────────────────────────┐
│ 题目/知识/题解/记录   │ 工具栏 + 代码编辑器       │
│                      ├──────────────────────────┤
│                      │ Case / 结果 / AI 解析      │
└──────────────────────┴──────────────────────────┘
```

首版编辑器：

- 行号
- 当前行高亮
- Python 语法高亮
- 自动缩进
- Tab/Shift+Tab
- Undo/Redo
- 等宽字体
- Dirty/Saving/Saved
- Ctrl/Cmd+S
- Revision SHA
- 稳定焦点与滚动

没有真实实现前不显示：

- 格式化
- 多语言切换
- 讨论
- 通过率
- 社区提交次数

---

# 9. 分阶段开发路线

## Phase 0：保存现有成果与建立新基线

### 动作

- 保留 `feature/real-user-iteration-20260831@fa0c10` 作为不可丢失检查点。
- 不把当前 `PARTIAL` 分支直接视为最终产品合并。
- 从该提交创建新的实现分支，例如：
  - `feature/product-v1-dynamic-interview`
- 将本 Plan 写入仓库。
- 创建 Draft PR，但标题必须说明：
  - foundation + dynamic redesign in progress
  - not release ready

### 验收

- 工作树干净
- 新分支基于正确 HEAD
- 当前报告和本 Plan 都可追溯
- 不丢失已有 PDF/DOCX、录音和转录代码

---

## Phase 1：视觉方向冻结

### 交付

- 三套统一编程工作台高保真方向
- 每套深浅色
- 真实题面、编辑器、Case、运行结果
- 悬浮、焦点、选中、错误、运行中、成功状态
- 视觉对比说明

### 约束

- 此阶段不批量重写所有 QML
- 不做全量回归
- 只做原型或最小页面实现

### Gate

由产品负责人明确选定一个方向。

---

## Phase 2：基础可靠性和产品入口

### 范围

- Profile 创建后重启恢复
- 上次使用 Profile 自动进入
- Profile 切换
- 首题可正常打开
- 默认中文
- 设置中切换英文
- 修复文字覆盖、错位和遮挡
- Codex 自动发现与路径说明
- No-AI 面试锁定页
- 结构化错误码
- 异步重复点击门控

### UAT

- 创建 Profile → 退出 → 重启 → 不重复创建
- 首题点击后进入真实工作台
- 900×620、1080×680、1280×800、1440×900 无关键文本遮挡
- No-AI 点击面试后看到解锁说明而不是假面试

---

## Phase 3：统一编程题工作台

### 子切片

#### 3A 工作台壳

- SplitView
- 中文题面
- 编辑器
- Console

#### 3B 可见 Case

- 选择 Case
- 运行
- 实际输出
- Stale 标记

#### 3C 正式验证

- 保存
- 完整测试
- SHA 绑定
- 提交记录
- Review 入口

#### 3D AI 解析

- 显式上下文预览
- 绑定 Problem ID、Submission SHA、Test Operation ID
- 没有 AI 时不显示空 Tab

#### 3E Interview 复用

- 计时保留
- 隐藏知识、答案和提示
- 只显示 1–2 个样例
- 锁定提交
- Grader 证据进入 Interview Turn

### Gate

Practice 与 Interview 使用同一个 Workbench，不允许复制两套实现。

---

## Phase 4：官方答案与内容治理

### 工程

- 设计官方答案目录和 Schema
- 更新 Catalog
- 更新 AGENTS/CONTRIBUTING
- 更新 Artifact 检查
- 更新 AI 读取边界
- 建立官方答案验证脚本

### 内容

先覆盖：

- 三条 Golden Quest
- 综合关卡
- 高频面试 Coding

### 产品

- 正式验证通过后解锁
- 放弃独立作答后解锁
- Assisted 状态
- 新变式要求
- Strict Mock 排除已看答案原题

---

## Phase 5：材料管线完善

### 范围

- PDF/DOCX 提取预览
- 提取质量
- 原文件与文本独立授权
- Provider 原始文件能力
- 使用上次材料组合
- 默认预选上次材料
- 材料漂移提醒
- 面试报告材料使用记录

### Gate

任何原始文件离开本机前必须单独确认。

---

## Phase 6：动态文字面试

### 6A Session v2 和兼容读取

- 新 Schema
- Old Session 可读
- 不迁移未发布的未来问题计划
- 新 Session 不存未来问题

### 6B Coverage Contract

- 全部岗位
- 岗位差异
- Coding 默认规则
- 时间预算
- 必选/可选能力

### 6C Provider Adapters

- 普通 Chat Provider
- Codex App Server
- 统一 Turn 协议
- Retry/Pause

### 6D 动态逐轮生成

- 当前问题
- 回答冻结
- 内部分析
- 下一问生成
- 连贯追问
- 自然切换主题
- 时间收敛

### 6E 训练/模拟双模式

- 可见性规则
- 提示和重答
- 即时反馈
- Strict Mock 隐藏内部状态

### 6F Coding Round

- 本地选题
- 最近做过/已 Mastered 可复测
- 已看官方答案原题排除
- Workbench 切换
- Grader 证据

### 6G 报告

- 公共维度 + 岗位维度
- 客观 Grader 与 AI 主观判断分离
- 完整/部分证据
- 证据跳转
- 材料使用情况
- Token Usage

### 6H 异常恢复

- Provider 失败
- 应用崩溃
- 当前问题恢复
- 下一问生成重试
- 报告生成重试

---

## Phase 7：文字版内部真实验收

此阶段不公开发布，但必须由产品负责人完成真实流程：

```text
导入 PDF 简历
→ 复用上次材料
→ 确认本场授权
→ 选择 Provider
→ 开始严格模拟
→ 项目深挖
→ 动态追问
→ 八股/场景
→ Coding
→ 候选人反问
→ 报告
→ 退出重启查看记录
```

至少验证：

- Codex
- 一个真实 OpenAI-compatible Provider
- 本地 Ollama（若继续宣称支持）
- 无材料通用面试
- 有材料个性化面试
- 训练模式
- 严格模拟
- Provider 中断与恢复

发现的核心问题修完后才进入本地语音产品化。

---

## Phase 8：本地语音产品化

### 8A 本地 STT

- 模型包管理
- 下载、校验、删除
- CPU/GPU/Apple Silicon 能力
- 麦克风权限
- 录音格式
- 失败恢复

### 8B 远程 STT 高级选项

- 复用现有 OpenAI-compatible 适配器
- 独立授权
- 费用和隐私提示
- 不作为默认路径

### 8C 本地 TTS

- 男/女正式自然声音
- 试听
- 下载
- 语速
- 自动播放
- 重播
- 文字降级

### 8D Transcript

- 训练可编辑
- Strict Mock 原始证据不可覆盖
- 复盘副本
- STT 错误标注

### 8E 音频策略

- 默认转录成功后删除
- 用户可开启本地保留
- 单独删除和导出

### 8F 设备异常

- 麦克风占用
- 音频设备断开
- STT 加载失败
- TTS 加载失败
- 自动暂停/文字降级

---

## Phase 9：最终跨平台验收

### Windows

- Standalone Portable ZIP
- Explorer 双击
- 中文/空格路径
- AppData
- Credential Manager
- 麦克风权限
- 本地 STT/TTS
- 损坏资源错误框
- 900×620 到 1440×900

### macOS

- Apple Silicon App/DMG
- Finder 启动
- Application Support
- Keychain
- 麦克风权限
- 本地 STT/TTS
- Gatekeeper 真实说明
- 深浅主题

### Provider

- Codex
- OpenAI-compatible
- Ollama（若发布声明支持）
- 原始文件能力与文本后备
- Usage 有/无两类 Provider

### 隐私

- 无真实 Profile
- 无 Key
- 无材料正文
- 无录音
- 无 Transcript
- 无官方测试/私有资产泄露
- 原始文件发送必须有证据

---

## Phase 10：RC 与发布

只有以下全部满足才允许：

- 文字版完整验收通过
- 语音版完整验收通过
- Windows 实机通过
- macOS 实机通过
- 一次最终本地全量通过
- 一次 RC CI 通过
- Artifact 隐私检查通过
- 文档、版本、Tag、Release Notes 一致
- 无已知 P0/P1 阻断
- 报告不再是 `PARTIAL`

---

# 10. 测试与迭代预算

## 10.1 开发阶段

每个垂直切片只运行：

- 直接单元测试
- 直接集成测试
- 受影响 QML Smoke
- 必要截图

禁止：

- 每个小改动都跑全量
- 每个子 Agent 跑全量
- 多次重复完整 CI
- 为了“保险”写大量无需求支持的防御代码
- 尚未选定视觉方向就批量改所有页面

## 10.2 大 Gate

计划只设置两次主要全量门：

1. 文字版 Phase 7 内部验收前后的一次集成全量
2. 最终 Phase 10 RC 的一次全量 + 一次 RC CI

若全量失败：

- 只修失败
- 先跑失败用例
- 不立刻重跑整个矩阵
- 修复集合稳定后再执行 Gate

## 10.3 必测核心

- 动态下一问受上一轮回答影响
- Strict Mock 中不存在未来问题泄露
- Session 文件不包含未来问题
- 材料授权逐场有效
- 上次材料仅预选、不自动发送
- 已看官方答案原题不进入严格评分
- 最近做过/已 Mastered 可作为复测题
- 代码 SHA 与 Grader 证据一致
- 修改代码后旧结果 Stale
- 不完整面试无完整总分
- 原始 Transcript 不被复盘修正覆盖
- Provider 异常不跳过当前问题
- TTS 故障不阻塞文字面试
- STT 故障进入暂停或允许文字降级
- Profile 切换不串状态

---

# 11. 最终验收清单

## 11.1 首次使用

- 创建一次 Profile
- 退出重启不重复创建
- 默认中文
- 可切换英文
- 首题可打开
- 无文字覆盖

## 11.2 刷题

- 中文题面
- 样例运行
- 正式验证
- 提交记录
- 官方答案解锁
- Assisted 证据
- AI 解析
- D+2/D+7

## 11.3 模拟面试

- No-AI 锁定
- 有 AI 可开始
- 无材料可通用面试
- 有材料可个性化
- 复用上次材料
- 不提前展示未来问题
- 后续问题依赖前序回答
- 可跳过
- 可澄清
- Coding
- 候选人反问
- 时间收敛
- 中断恢复
- 完整和部分报告

## 11.4 语音

- 本地录音
- 本地 STT
- 可选远程 STT
- 本地 TTS
- 男/女声
- 训练/严格模式
- 原始 Transcript
- 复盘副本
- 音频删除/保留

## 11.5 报告

- 0–100 总分
- 1–5 维度
- 不完整无总分
- 证据跳转
- 材料使用记录
- Grader 与 AI 分离
- 未覆盖项
- 置信度
- 无 Offer 概率

---

# 12. Definition of Done

项目只有在以下条件全部成立时才算完成本 Plan：

1. 现有真实用户反馈中的重复创建、首题打不开、默认英文、文字覆盖、Codex 发现困难和材料错误都已解决。
2. 统一编程工作台成为 Practice 与 Interview 的唯一 Coding UI。
3. 官方答案有经过验证的首批覆盖，并正确影响 Mastery 和面试选题。
4. 严格模拟面试不预生成、不保存、不展示未来问题。
5. 每道下一问确实基于用户背景、本场前序对话和当前回答生成。
6. Codex 与普通 API 共用同一面试业务流程。
7. PDF/DOCX 可本地提取，原始文件和文本独立授权。
8. 上次材料组合可复用，但不自动发送。
9. 最近做过和已 Mastered 的题可用于复测；已看答案原题不用于严格评分。
10. 本地 STT 为默认；远程 STT 为可选；TTS 始终本地。
11. 报告带证据，部分面试不伪装成完整面试。
12. Windows 和 macOS 均有真实平台验收。
13. 最终全量和 RC CI 通过。
14. 不默认上传任何用户材料、Transcript、代码或音频。
15. 最终公开版本的说明、行为和实际实现一致。

---

# 13. 对后续 Codex 的交接原则

后续执行 Prompt 必须明确告诉 Codex：

- 先读本 Plan，再读现有 `REAL_USER_ITERATION_FINAL_ZH.md`。
- 不得把当前“预生成个性化计划”当作最终需求。
- 不得删除已有 PDF/DOCX、录音、远程转录和隔离机制；应重用并重构。
- 不得先做全量大重构。
- 按本 Plan 的 Phase 和 Gate 做垂直切片。
- 视觉方向未经人工选定前，不批量替换所有页面。
- 子任务只跑定向测试。
- Main Agent 负责产品边界、集成和验收。
- 不得声称 `507 passed` 能覆盖后续新增的大量功能。
- 未完成 Windows/macOS、真实 Provider、本地 STT/TTS 和 RC CI 前，不得发布。
