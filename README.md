# LLM Interview Lab

一个面向大众的、开源的 AI 算法面试手撕训练平台。

项目不把“一次测试通过”当作掌握，也不提供可直接复制的公共完整答案。固定课程、公开测试和解锁关系保持确定性；AI 可以解释、提示、审查和生成本地变式，但不能替学习者证明自己已经掌握。

当前版本是 **LEAN-V2 Vertical Slice 1**：它先用一题打通完整工程闭环，再根据真实使用反馈扩展课程，而不是预先创建数百个空目录。

## 核心特点

- **Clone-first**：clone 一个仓库即可训练，不要求第二个项目或数据库；
- **Repository-local Workspace**：个人答案和历史默认位于仓库内的 `workspace/profiles/<profile_id>/`；
- **Git 隐私隔离**：真实 Profile 默认被 `.gitignore` 排除；
- **Curriculum first**：课程节点、依赖、接口和测试契约由固定 Catalog 决定；
- **答案隔离**：公共题目只有题面、starter、公开测试和分级提示；
- **显式 submission grading**：课程测试只测试 Workspace submission，不会偷偷 import starter；
- **Retention gates**：implemented、reviewed、D+2、D+7 与 mastered 是不同状态；
- **AI at the edges**：AI 负责教学和个性化，本地确定性工具负责基础事实与测试证据。

## 五分钟开始

推荐 Python 3.11；项目最低版本保持 Python 3.10。

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
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

安装并创建本地 Profile：

```bash
python -m pip install -r requirements.txt
llm-lab init --profile default
llm-lab doctor
llm-lab next --profile default
```

`requirements.txt` 只是兼容入口；依赖及版本范围只在 `pyproject.toml` 维护。

新 Profile 不要求姓名、公司或简历。初始化只会生成本地配置、空学习历史和必要目录。

## 完成第一题

当前固定课程只有一个 ready 节点：

```text
FND-001 Wrong Prediction Count
```

查看并开始：

```bash
llm-lab show FND-001
llm-lab start FND-001 --profile default
```

`start` 将无答案 starter 复制到：

```text
workspace/profiles/default/submissions/FND-001/attempt-0001/submission.py
```

编辑这个本地文件，然后运行：

```bash
llm-lab test FND-001 --profile default
llm-lab submit FND-001 --profile default
llm-lab next --profile default
```

首次 `test` 预期失败，因为 starter 没有实现。课程测试由 grader 精确运行，并通过统一 plugin 注入当前 submission；不会导入 `starter.py`，也不会扫描其他 Profile。

`submit` 只接受与当前文件 SHA-256 匹配的 passing test evidence。成功后状态最多是 `implemented`：

```text
Public tests: PASS
Contract review: PENDING
Oral defense: PENDING
D+2 retention: PENDING
D+7 retention: PENDING
Mastery: NOT YET
```

## 第一版 CLI

| 命令 | 是否写 Workspace | 用途 |
|---|---:|---|
| `llm-lab doctor` | 否 | 校验环境、Catalog、DAG、虚构 Demo 和 Git 隔离 |
| `llm-lab init --profile <id>` | 是 | 创建或验证一个本地 Profile |
| `llm-lab next --profile <id>` | 否 | 一屏展示当前任务和最多三个解锁项 |
| `llm-lab show <problem_id>` | 否 | 展示固定题目契约 |
| `llm-lab start <problem_id> --profile <id>` | 是 | 创建或幂等返回当前 attempt |
| `llm-lab test <problem_id> --profile <id>` | 是 | 运行精确公开测试并写测试事件 |
| `llm-lab submit <problem_id> --profile <id>` | 是 | 记录 submission 和 implemented 证据 |

本切片不包含 Web UI、数据库、账户系统、网络服务、多 Agent Runtime 或恶意代码沙箱。`llm-lab` 只执行学习者本人信任的本地代码；路径检查用于防止误加载，不构成安全隔离。

## Workspace 与隐私

公共仓库跟踪：

```text
workspace/README.md
workspace/schema/
workspace/templates/
workspace/demo/
workspace/profiles/.gitkeep
```

本地真实数据默认忽略：

```text
workspace/profiles/<profile_id>/
├── profile.yaml
├── events.jsonl
├── submissions/
├── generated/
├── private_tests/
├── reviews/
├── cache/
└── exports/
```

可以验证隔离：

```bash
git check-ignore -v workspace/profiles/default/events.jsonl
git status --short
git ls-files workspace/profiles
```

最后一条命令在公共仓库中只应显示 `.gitkeep`。不要使用 `git add -f` 添加真实 Profile。

`workspace/demo/` 完全虚构，只用于 CI。CI 不读取真实 Profile；发布包也不应包含它们。

## 唯一事实源

LEAN-V2 新闭环使用两类事实源：

```text
curriculum/catalog/*.yaml
    固定课程节点、前置关系、接口、Runner、Oracle 和变式契约

workspace/profiles/<profile_id>/events.jsonl
    该 Profile 的学习历史；物理行顺序就是 reducer 顺序
```

Workspace 只引用 Problem ID，不复制课程定义。当前任务、进度、帮助统计和复测状态应由事件生成，不由用户同时维护多份 Markdown。

旧 `curriculum/catalog.json`、`state/` 和相关脚本暂时保留为兼容层；Vertical Slice 1 不删除或改写其历史。它们不会被新 `llm-lab` 当作新 Profile 的事实源。

## 题目结构

一个 ready 固定题默认只有四个文件：

```text
curriculum/problems/<id>-<slug>/
├── task.md
├── starter.py
├── test_public.py
└── hints.md
```

结构化元数据只存在于 `curriculum/catalog/*.yaml`，不在题目目录重复维护。`planned` 节点只应存在于 Catalog；当前切片尚未登记大规模 planned 目录。

公共仓库不提供真正隐藏测试。个性化变式和私人测试未来只进入本地 Workspace，不会自动加入公共课程。

## AI 如何协助

学习者可以让能读取仓库的 AI：

- 解释当前题目的概念、输入输出和边界；
- 按 H0–H5 控制提示强度；
- 审查 Workspace submission 与测试证据；
- 追问复杂度、异常、张量 shape 或数学原理；
- 根据错误生成本地调试题和复测建议；
- 检查“测试通过但契约未满足”的情况。

AI 默认不应直接完成当前 submission，也不能仅凭测试通过写入 mastered。详细行为边界见 [AI 教练协议](docs/COACHING_PROTOCOL.md)。

## Repository Health

根 pytest 只收集基础设施和已接受回归，不自动运行课程 starter 或 learner submission：

```bash
python -m pytest --collect-only -q
python -m pytest -q
llm-lab doctor
```

旧兼容校验继续保留：

```bash
python scripts/check_environment.py
python scripts/validate_curriculum.py
python scripts/validate_external_courses.py
python scripts/validate_state.py
python scripts/export_handoff.py --dry-run
```

当前旧训练 fixture 的精确测试仍可显式运行，但它不是 Repository Health：

```bash
python -m pytest tests/stage00/test_task_00a1.py -q
```

## 兼容层说明

早期版本提供 `scripts/create_private_workspace.py`，把公共 HEAD 复制成第二个私有仓库。该脚本和 Makefile 本切片继续保留，供已有用户迁移或回滚；它不再是新用户默认入口。

现有外部课程 metadata 和固定 checkout 工具也继续保留，但不会被 `llm-lab init`、`next` 或 FND-001 自动启用。外部官方作业的 AI 帮助边界仍以其 Task Card 和上游政策为准。

## 项目边界

本仓库可以包含原创 toy problem、公开数据、公开论文/API 来源和完全虚构 Demo。不得提交：

- 公司、客户或其他第三方的内部代码、数据、配置或指标；
- 真实学习记录或简历事实；
- 模型权重、日志、凭据或本地绝对路径；
- 第三方题面、测试、starter、提示或答案的未授权复制；
- 固定课程的公共完整答案。

安全和来源政策见 [SECURITY.md](SECURITY.md) 与 [参考资料政策](docs/REFERENCE_POLICY.md)。

## 当前状态与贡献

当前是 alpha 纵向切片，不代表完整课程已经可用。只有 FND-001 已进入新固定 Catalog；Tensor、Loss、Optimizer、Transformer、VLM、后训练、Agent、推理和分布式节点尚未写入本切片。

欢迎提交小而可验证的基础设施、测试和原创课程改进。现阶段不要批量生成空题目目录，也不要提交公共答案。贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

License: [Apache-2.0](LICENSE).
