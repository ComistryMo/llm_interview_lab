# Golden Quest 真实体验指南

本指南用于真实 Alpha 学习者验证，不是自动遥测。不要在 Issue 中上传答案、Workspace、雇主数据、真实姓名、公司、邮箱、Private Tests 或任何保密材料。

## 1. 安装

优先使用 README 的桌面下载；源码用户执行：

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
python -m pip install -e ".[dev]"
llm-lab init --profile beta-local --track ai_foundation
```

## 2. 完成 Python Data Reliability

```text
FND-001 → FND-002 → FND-003 → FND-004 → FND-005 → FND-006
→ CAP-FND-001 Hard Sample Data Pipeline
```

每题完成公开测试、契约审查、口述答辩、D+2 与 D+7。不要查看旧答案完成复测。综合关卡只在六题 `mastered` 后解锁。

## 3. 记录最小反馈

通过 [Alpha 体验反馈模板](https://github.com/ComistryMo/llm_interview_lab/issues/new?template=beta.yml) 记录：背景类别、安装耗时、首次任务耗时、完成节点、路线完成度、契约困惑、误导测试、提示泄漏、D+2 / D+7 价值、阻断 Bug 和自由反馈。

`field_runs` 只能来自真实外部使用记录，自动 E2E 不算真实 Field Run。当前没有真实记录时保持 0。
