# 岗位画像、技能与面试蓝图

适用版本：v0.4.0-alpha.4。新桌面面试不再区分实习／校招／有经验，岗位决定范围，授权背景决定切入点，难度决定深度和压力；同样证据使用同样评分锚点。

岗位感知训练复用公共对象，不复制固定课程：

```text
Problem / Interview Item → 教授或评估 → Skill
Skill → 定义技能范围 → RoleProfile
RoleProfile + 难度 + 授权背景 + 已发生问答 → 动态下一问
```

学习路径仍由 Track、Quest 与 Capstone 表达。岗位画像只引用这些对象，不维护第二份题目列表。

## 技能等级

每项规范技能使用 0–4 级：

| 等级 | 含义 |
|---:|---|
| 0 | 未接触 |
| 1 | 能解释基本概念 |
| 2 | 能在提示下实现或分析 |
| 3 | 能独立实现、调试并解释权衡 |
| 4 | 能做系统设计、优化或指导他人 |

自评与验证证据分开。简历中出现一个关键词不会自动提高验证等级。

## 八类岗位

### AI 产品经理

重点：用户与问题定义、AI 能力边界、PRD、产品指标、离线 / 在线评测、成本时延质量、安全回退、A/B Test、数据闭环和跨团队沟通。

### AI 应用工程师

重点：LLM API、Prompt、Structured Output、RAG、Tool Calling、Agent Loop、评测、Observability、缓存、降级、部署和成本。

### AI Agent 工程师

重点：Tool Schema、Parser、Executor、State、Memory、Planning、Trajectory、长轨迹、错误恢复、Agent Eval 与 Agent SFT / RL。

### AI 算法 / 研究工程师

重点：ML / DL 数学、PyTorch、Transformer、VLM、数据、Loss、Optimizer、实验设计、误差分析、复现和机制解释。

### 大模型后训练工程师

重点：SFT、Preference Data、DPO、Reward Model、PPO / GRPO / DAPO、Verifier、Rollout、Reward Hacking、数据飞轮和训练稳定性。

### AI Infra / ML 平台工程师

重点：数据与训练平台、调度、分布式训练、Checkpoint、容错、资源利用、Pipeline、版本治理、成本、可靠性与 MLOps。

### AI 推理 / 系统工程师

重点：KV Cache、Continuous Batching、PagedAttention、Prefix Cache、量化、Speculative Decoding、CUDA / Triton、Kernel Profiling、延迟吞吐显存和 Serving 调度。

### AI 评测 / 数据 / 安全工程师

重点：数据质量、Benchmark、采样、标注一致率、污染检测、LLM-as-a-Judge、Rubric、安全评测、Red Team、线上监控和统计分析。

Alias 只映射到这些公共画像，例如 AI Application Engineer → AI 应用工程师、ML Systems Engineer → AI Infra，不复制 Skill 或 Blueprint。

## 历史静态面试蓝图（兼容资产）

24 个旧蓝图保留岗位、求职阶段、轮次、权重和选题规则，以恢复历史会话与兼容静态 CLI；包含 `intern`、`new_grad` 与 `mid`。**新动态面试不按这些字段选蓝图、时长、候选题或评分要求**，也不将旧 Profile 分档偷偷转换为默认值。

典型结构：

```yaml
role: ai_infra_engineer
seniority: new_grad
duration_minutes: 90
rounds:
  - type: coding
    duration: 30
    weight: 0.25
  - type: system_design
    duration: 30
    weight: 0.35
  - type: project_deep_dive
    duration: 20
    weight: 0.25
  - type: behavioral
    duration: 10
    weight: 0.15
```

Coding 题只选择 Catalog 中 `ready` 且 validation 为 `oracle / field / stable` 的节点。非代码题使用公开 Rubric，评分必须引用回答证据并区分事实、推断与遗漏。

## 报告解释

面试报告包括 Overall Summary、Skill Scores、Strong Evidence、Critical Gaps、Uncertain Areas 和推荐 Problem / Quest。缺少证据的维度标记 `unscored` 或 `incomplete`，不能重新归一化凑分。

报告不是 Offer 概率，也不修改 Practice mastery。

## 维护岗位与兼容蓝图

新增前先回答：

1. 是否能用现有 Role Alias 表达；
2. 所有 Skill ID 是否已存在；
3. 是否复用了现有 Track / Quest，而不是复制题目；
4. 是否避免向新动态流程引入求职阶段分档；旧权重变动是否会影响历史协议；
5. Blueprint 的轮次、时间和评分能否完成一次 E2E；
6. 固定 Item 是否原创、有 Rubric、经过 Maintainer Review 和模拟面试。

运行：

```bash
python -m pytest tests/infrastructure/test_role_interviews.py -q
python -m pytest tests/infrastructure/test_unified_interview.py -q
```
