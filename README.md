# LLM Interview Lab

[![CI](https://github.com/ComistryMo/llm_interview_lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ComistryMo/llm_interview_lab/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

一个以“独立实现、证据审查、间隔复测”为核心的大模型算法面试训练实验室。它把 AI 放在教练席，而不是代写席。

> Project status: **v0.1 alpha**. B00 基础设施与 Task 00A-1 流程 fixture 可用；00A-2 之后的 Stage 00 内容仍是 draft。仓库目前保留一个脱敏但与维护者公开账号关联的 fixture，因此尚未启用 GitHub Template。新用户必须先生成无答案的私人 workspace，不能把 fixture 当作自己的训练证据。

## 它解决什么问题

常见学习计划记录“看过什么”，却无法回答“能否闭卷写出、解释边界、七天后迁移”。本项目用同一条证据链管理每个任务：

```text
唯一任务 → 独立尝试 → 定向测试 → 需求审查 → 原理口述
        → D+2 闭卷复写 → D+7 变式 → 综合迁移
```

- `src/` 保存学员答案，AI 默认只读；
- `tests/` 把正常、边界、异常和性质要求变成可执行证据；
- `state/TASK_LEDGER.jsonl` 记录帮助等级和状态迁移；
- `curriculum/`、`hints/` 将任务文字、分级提示与完整答案分开；
- 课程可按依赖阶段或岗位方向浏览，runtime、GPU 策略和可见测试均有机器可读登记；
- 通用教练协议可供具备终端能力、只读文件能力或纯聊天能力的 AI 使用。

它与“答案型算法教程”的边界很明确：这里不把完整答案与当前练习放在一起，核心产物是受控 AI 帮助下的独立实现、审查、D+2/D+7 复测和迁移证据。外部优秀项目只作为固定版本的设计参考，不作为课程内容镜像。

## 适合与不适合

适合正在准备 LLM/VLM、后训练、Agent 或算法工程岗位，愿意接受单任务、限时、闭卷和变式复测的学习者。它不是完整 Python 教材、题库镜像、公司项目资料库，也不承诺用一套固定路线适配所有人。

## 10 分钟开始

要求：Git、Python 3.10+。PyTorch 在 Tensor 阶段前是可选依赖。

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git llm-interview-lab-upstream
cd llm-interview-lab-upstream
python scripts/create_private_workspace.py ../my-llm-interview-lab
cd ../my-llm-interview-lab
python -m venv .venv
```

激活环境：

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
. .venv/bin/activate
```

安装最小依赖并检查仓库健康：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_environment.py
python -m pytest -q
python scripts/validate_curriculum.py
python scripts/validate_state.py
```

`python -m pytest -q` 只运行基础设施与已验收回归，必须全绿。当前训练题使用 `state/CURRENT_TASK.md` 里的定向命令；训练中的红灯是反馈，不等于仓库损坏。

生成器只读取已提交的公共 HEAD，不复制源 checkout 的未提交文件；它清除 fixture、恢复无答案 starter、创建新的 `not_started` ledger，并丢弃公共 Git 历史。结果是一个全新、尚未提交但已暂存待审查的 `main` 分支；`upstream` 只可 fetch、不可 push。添加私人 `origin` 和填写档案前，按[开始使用](docs/GETTING_STARTED.md)完成安全检查。

## 与 AI 协作

先让 AI 读取 `AGENTS.md`、学习者档案、当前任务、教练协议和任务卡，再要求它只推进一个问题。通用启动文本：

```text
开始今日训练。读取仓库规则和当前任务，运行定向测试；
不要修改我的答案。用不超过 10 条复述状态，然后只给出唯一下一步。
```

本仓库原生提供 `AGENTS.md` 入口；其他助手按[AI 教练接入指南](docs/AI_COACH_ADAPTER.md)使用同一份权威协议。任何助手都不得因为工具能力更强而绕过帮助等级或 mastery Gate。

## 公共和私人边界

这个 GitHub 仓库是公共上游：课程、协议、模板、测试基础设施、虚构示例和一个明确标注的脱敏维护者 fixture 可公开。你的真实档案、答案、审查、进度和项目事实应保存在生成的**独立私人仓库**，不要放在公共 fork 中。

`.gitignore` 不是保密机制。雇主或客户的源码、数据、日志、路径、配置、截图、模型标识、指标和业务样本，连“被忽略的本地目录”也不应进入本仓库工作树。详见[隐私与安全](docs/PRIVACY_AND_SECURITY.md)。

## 关键命令

| 目的 | 命令 |
|---|---|
| 环境检查 | `python scripts/check_environment.py` |
| 创建私人 workspace | `python scripts/create_private_workspace.py <new-directory>` |
| 默认健康测试 | `python -m pytest -q` |
| 当前任务 | 读取 `state/CURRENT_TASK.md` 中的命令 |
| 课程目录一致性 | `python scripts/validate_curriculum.py` |
| 状态一致性 | `python scripts/validate_state.py` |
| 导出预检 | `python scripts/export_handoff.py --dry-run` |
| 可选 Torch 环境 | `python -m pip install -r requirements-torch.txt` |

## 文档导航

- [开始使用](docs/GETTING_STARTED.md)
- [教练协议](docs/COACHING_PROTOCOL.md)
- [状态模型](docs/STATE_MODEL.md)
- [评分量表](docs/ASSESSMENT_RUBRIC.md)
- [个性化](docs/CUSTOMIZATION.md)
- [AI 接入](docs/AI_COACH_ADAPTER.md)
- [测试边界](docs/TESTING.md)
- [仓库架构](docs/REPO_ARCHITECTURE.md)
- [课程双轴导航](curriculum/NAVIGATION.md)
- [课程元数据契约](docs/CURRICULUM_METADATA.md)
- [课程路线](docs/MASTER_TRAINING_PLAN.md)
- [外部参考与来源治理](docs/REFERENCE_POLICY.md)
- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)

## 贡献与许可证

课程 PR 必须包含前置任务、可见测试、分级提示、D+2/D+7 变式和隐私确认；不要提交完整学员答案或批量空任务。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

本项目采用 [Apache License 2.0](LICENSE)。
