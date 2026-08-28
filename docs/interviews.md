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

## 把真实面试问题留档

只记录你有权保存、已脱敏的题目和个人复盘。不要复制面试平台的受版权保护原文或公司内部材料。留档用于私人复盘，不会自动进入公共固定题库；公共化仍需 Schema、Rubric、版权、重复度、真实验证与 Maintainer Review。
