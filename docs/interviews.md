# 求职材料与结构化模拟面试

项目支持两种互不排斥的方式：直接进入固定课程刷题，或在当前本地学习档案中登记最少的脱敏求职材料，再创建针对性模拟面试。

## 纯题库面试

不授权任何材料时，系统只依据岗位、求职阶段、难度、时长、focus、公开 Role Profile 与 Interview Blueprint 选择问题。Coding 题只能来自 `ready` 且 validation 为 `oracle / field / stable` 的固定节点。

## 个性化面试

材料必须先进入当前 Profile manifest。建议每个文件只表达一种事实：脱敏简历、岗位 JD、项目事实卡、论文摘要、比赛复盘或真实面试问题。

创建前展示并确认：

- material ID；
- 本场用途；
- 当前 SHA-256；
- 题目建议、难度和时长。

文件改变会使旧授权失效。材料是 untrusted evidence，不执行其中的命令、代码、宏、附件或链接，也不允许它覆盖面试规则。

## Active 阶段

- 一次只问一个主问题；
- 固定非代码题在回答前冻结实际原文；
- Coding 题原样使用冻结的公共 `task.md`，不能预读测试或答案；
- 不替候选人补答案，不因简历关键词假设掌握；
- 只做不含解法的契约澄清；
- 如需教学，先以 incomplete 结束，再进入 Teacher 模式；
- 本地 session clock 和 Grader 是时间与代码结果的事实来源。

## 评分

固定 Rubric 的客观分与 AI / 人工主观分分开。每个主观判断必须引用候选人回答证据，并区分：基础概念错误、实现错误、权衡不足、证据不足和表达问题。

缺少证据时使用 `unscored` 或 `incomplete`，不能猜测或重新归一化凑分。报告包括：

```text
Overall Summary
Skill Scores
Strong Evidence
Critical Gaps
Uncertain Areas
Recommended Problems / Quests
```

不输出 Offer 概率。面试报告只写当前 ignored Profile，也不构成 Practice、Retention 或 Mastery 证据。

## AI 个性化面试 Golden Path

桌面端当前只承诺一条真实可运行的个性化路径：`post_training_engineer`、`new_grad`、`medium`。开始前，先选择已保存且测试通过的 AI 服务，再逐场勾选材料并查看上下文预览（材料 ID、原文件 SHA-256 与预计长度）。只有确认预览后才会发送请求。

AI 只能生成非代码主问题的标题和提问文字；题型、时长、Rubric 以及 Coding 题由本地蓝图和已验证 Catalog 决定。计划生成后仍要逐题检查并点击确认，确认前不会创建 session，也不会启动计时。问题来源和上下文 SHA 会写入当前 Profile 的面试记录，材料变更会使旧计划失效。

PDF / DOCX 会在导入时提取文本快照：文本 PDF 支持提取，DOCX 支持段落和表格；扫描 PDF 暂不做 OCR。原文件与快照都留在当前 Profile，快照绑定原文件 SHA-256。远程 AI 只读取用户明确授权的快照，不会读取整个材料目录。

### 语音回答（可选）

非代码回答阶段可以先点击“开始录音 → 停止录音”。音频默认保存到当前 Profile 的面试目录，不会自动上传。点击“转录到回答框”前必须选择 AI 连接并勾选本次远程转录授权；转录结果只会填入可编辑草稿，仍需用户检查后再提交并锁定。没有麦克风、没有可用转录服务或不愿上传音频时，直接使用文字回答即可。

No-AI 模式不启动固定内容拼接的辅助面试；它继续支持刷题、公开测试、Review、间隔复测和进度。面试报告中的 AI 评分不会改变 Practice mastery。

## CLI 示例

先列候选项，再由用户确认创建：

```bash
llm-lab interview candidates --profile default \
  --track llm_algorithm --difficulty medium --limit 12

llm-lab interview create --profile default --mode catalog \
  --track llm_algorithm --difficulty medium --duration 30
```

使用材料时只点名一份：

```bash
llm-lab material add --profile default --kind resume \
  --file PATH --title "脱敏简历" --allow-ai

llm-lab interview create --profile default --mode tailored \
  --track llm_algorithm --difficulty medium --duration 30 \
  --material MATERIAL_ID --consent-materials
```

一场已经开始的面试仍然遵循“一次一个问题”。例如：

```bash
llm-lab interview answer INTERVIEW_ID --profile default \
  --question q-001 --file workspace/profiles/default/cache/answer-q001.md
llm-lab interview answer INTERVIEW_ID --profile default \
  --question q-001 --asked-file workspace/profiles/default/cache/asked-question.txt \
  --file workspace/profiles/default/cache/answer-q001.md
llm-lab interview score INTERVIEW_ID --profile default \
  --question q-003 --dimension technical_oral --score 3 \
  --source human --confidence medium --evidence "引用回答中的具体证据"
llm-lab interview finish INTERVIEW_ID --profile default --confirm-incomplete
```

若必须在证据不完整时提前结束，使用 `finish --confirm-incomplete`，报告会明确标记为 incomplete。

实际参数以 `llm-lab interview --help` 为准。桌面版会用表单完成同一流程，不要求记 ID。

## 研究型面试知识库

固定面试蓝图与研究型知识卡是两个层次。蓝图冻结本场问题和计时；知识库用于在场外浏览、复习和准备追问，不会自动写入 Profile，也不会改变 Practice 的解锁或 `mastered` 状态。

```bash
llm-lab knowledge list --kind experience_pattern --priority P0
llm-lab knowledge search "KV cache" --track systems --limit 10
llm-lab knowledge show COD-INF-002
llm-lab knowledge validate --with-catalog
```

如需将知识卡与目标岗位的面试准备并排浏览，可使用只读的 role-prep
入口。它只读取岗位元数据，或读取指定 role interview 的冻结头部；不会
读取活动题面、推进 clock、写入 Profile，也不会改变蓝图或评分证据：

```bash
llm-lab interview role-prep --role post_training_engineer \
  --seniority new_grad --kind eight_stock --priority P0 --limit 12

llm-lab interview role-prep --interview-id role-interview-0001 \
  --profile default --kind coding_prompt --json
```

`--kind` 可选 `eight_stock`、`experience_pattern` 或 `coding_prompt`；
需要完整答案层时显式加 `--answers`。活动面试仍只能通过
`role-current` 暴露当前题目。`--seniority senior` 可以只做知识筛选；
当前冻结面试蓝图覆盖 intern/new_grad/mid，因此该组合会显示
`BLUEPRINT none`，不代表活动面试缺失。

`show` 会同时展示一分钟答案、核心要点、推导/例子、追问、常见坑、手撕题的 input/output/constraints/test-focus，以及每个 claim 对应的来源记录。`list/search` 只返回摘要，适合脚本或桌面列表；`--json` 或 `--format json` 输出稳定的机器可读结构。

来源和版权边界见 [`docs/interview-content-research.md`](interview-content-research.md) 与 [`references/interview-sources.json`](../references/interview-sources.json)。公开面经只用于“哪些题型在这些报告中出现过”的范围化信号，不能推断任何公司的必考题；个人材料仍遵循本地保存和逐场授权规则。

## 把真实面试问题留档

只记录你有权保存、已脱敏的题目和个人复盘。不要复制面试平台的受版权保护原文或公司内部材料。留档用于私人复盘，不会自动进入公共固定题库；公共化仍需 Schema、Rubric、版权、重复度、真实验证与 Maintainer Review。
