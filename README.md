# LLM Interview Lab

> **Alpha v0.2.0-alpha.1:** 38 个可运行题中，13 个已通过维护者 public + private/property Oracle 验证，8 个具有经 Oracle 验证的 D+2/D+7 复测资产，0 个完成公开 field run。`ready` 表示题面与测试契约完整，不代表已经完成数值 Oracle 或真实用户验证。

本项目当前是公开 Alpha：欢迎试用与报告问题，但不承诺所有 `ready` 题都已完成数值验证。公共测试是学习反馈，不是防作弊的“隐藏测试”；本地 grader 有超时与输出截断，但不是恶意代码安全沙箱，只应运行你本人信任的代码。

一个面向大众的、clone 后即可使用的 AI 算法面试手撕训练平台。

这里训练的是“能独立解释、实现、测试、调试并隔周迁移”，不是把一次公开测试通过包装成掌握。固定课程与解锁规则是确定性的；AI 可以教学、分级提示、审查和生成本地变式，但不能直接判定 mastery。

## 五分钟开始

需要 Python 3.10+，推荐 Python 3.11。

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git
cd llm_interview_lab
python -m venv .venv
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
. .venv/bin/activate
```

激活环境后，在任一平台运行：

```bash
python -m pip install -e .[dev]
llm-lab init --profile default --track ai_foundation
llm-lab doctor
llm-lab next --profile default
llm-lab start FND-001 --profile default
```

编辑输出的 `workspace/profiles/default/.../submission.py`，然后运行：

```bash
llm-lab test FND-001 --profile default
llm-lab submit FND-001 --profile default
```

第一份 starter 预期测试失败；它不含答案。Tensor 及后续题另需：

```bash
python -m pip install -e .[torch,dev]
```

## 完整训练闭环

```text
init + Track
  → next → start → edit submission
  → test → submit (implemented)
  → contract + oral review (reviewed)
  → D+2 clean rewrite (retained_d2)
  → D+7 variant (mastered)
  → prerequisite unlock
```

结构化 Review 示例：

```bash
llm-lab review FND-001 --profile default \
  --contract passed --oral passed \
  --explanation "Explained validation and counting branches" \
  --complexity "O(n) time, O(1) auxiliary space" \
  --boundaries "Rejects bool, empty input, and invalid container types"
```

到期后启动全新、无旧答案的复测 attempt：

```bash
llm-lab retain FND-001 --stage d2 --profile default
llm-lab retain FND-001 --stage d7 --profile default
```

生产命令按 Review 事件时间计算 D+2/D+7；测试可以注入时钟。复测仍需 `test → submit → review`。只有公开测试、契约审查、口述、D+2 与 D+7 全部通过，确定性流程才写入 `task_mastered`。

## CLI

| 命令 | 作用 | 写 Workspace |
|---|---|---:|
| `llm-lab doctor` | 校验 Catalog、DAG、Demo 和 Git 隔离 | 否 |
| `llm-lab init --profile ID [--track TRACK]` | 创建本地 Profile | 是 |
| `llm-lab next --profile ID` | 一屏显示当前任务、复测和最多三个解锁项 | 否 |
| `llm-lab show PROBLEM` | 显示固定题契约 | 否 |
| `llm-lab start PROBLEM --profile ID` | 创建或幂等返回普通 attempt | 是 |
| `llm-lab test PROBLEM --profile ID` | 在独立 pytest 子进程运行公开测试 | 是 |
| `llm-lab submit PROBLEM --profile ID` | 绑定当前 SHA-256 测试证据 | 是 |
| `llm-lab review PROBLEM ...` | 记录结构化契约与口述结果 | 是 |
| `llm-lab retain PROBLEM --stage d2\|d7 ...` | 创建无旧答案的复测 attempt | 是 |
| `llm-lab catalog [--track TRACK]` | 主动展开完整目录 | 否 |
| `llm-lab graph --track TRACK` | 显示 Track DAG 边 | 否 |
| `llm-lab profile show ID` | 从 events 动态汇总状态 | 否 |

Tracks 包括 AI 基础、LLM、VLM、后训练、Agent、训练/推理系统，以及传统 ML、推荐、CV、GNN、生成模型和传统 RL 选修。

## 课程与差异化

当前固定图谱包含 38 个可运行题和 188 个 planned 节点。planned 节点只有 Catalog 元数据，不制造空目录。首批 ready 内容覆盖：

- 真实数据任务中的 Python 与 JSONL；
- shape、broadcast、gather、mask、last token、autograd；
- Stable Softmax、LogSumExp、BCE、Cross Entropy；
- SGD、Momentum、Adam、AdamW；
- Linear、Embedding、RMSNorm；
- Attention、MHA、MQA、GQA、RoPE、KV Cache；
- SFT label、sequence logprob、DPO、GRPO；
- Tool Schema、Registry、Agent Loop、Trajectory。

每个 ready 题只有原创 `task.md`、无答案 `starter.py`、`test_public.py` 和 H1/H2/H3 `hints.md`。元数据统一在 `curriculum/catalog/*.yaml`，包含前置、三维难度、Oracle、口述题、变式轴、不变式、常见错误和复测契约。

与普通题单相比，本项目把依赖解锁、提交 SHA、代码审查、口述、间隔复写和变式迁移放在同一个本地闭环中；课程测试只通过统一 loader 测试当前 Workspace submission，不会偷偷测试 starter。

## Workspace 与隐私

真实学习数据默认位于仓库内部但不进入 Git：

```text
workspace/profiles/<id>/
├── profile.yaml
├── events.jsonl          # 唯一学习历史事实源
├── submissions/
├── generated/
├── private_tests/
├── reviews/
├── cache/
└── exports/
```

公共仓库只跟踪 Schema、模板、完全虚构的 `workspace/demo/` 和 `.gitkeep`。验证方法：

```bash
git check-ignore -v workspace/profiles/default/events.jsonl
git status --short
git ls-files workspace/profiles
```

不要使用 `git add -f` 提交真实 Profile。更多边界见 [Workspace](docs/workspace.md)。

## AI 教练

把 [AGENTS.md](AGENTS.md) 与 [Coach Policy](coach/POLICY.md) 提供给能读取本地仓库的 AI。AI 可以：

- 运行 `next/show/test`，解释当前契约和失败证据；
- 按 H0—H5 控制提示；
- 审查代码可读性、复杂度、数值稳定、shape/mask/dtype/device/gradient；
- 完成结构化口述追问；
- 按 Catalog 的 `variant_axes` 在本地 `generated/` 创建私人变式和测试。

AI 不得修改固定 DAG、把生成题自动加入公共题库、替学习者补当前答案，或用测试通过直接写 mastery。项目不含模型 API、多 Agent Runtime 或后台服务。

## 开发与安全边界

```bash
python -m pytest --collect-only -q
python -m pytest -q
llm-lab doctor
python scripts/validate_external_courses.py
```

根 pytest 不收集课程 `test_public.py`、starter 或真实 Profile。Grader 提供精确路径、超时和输出截断，但不是恶意代码沙箱；只运行学习者本人信任的本地代码。

架构见 [docs/architecture.md](docs/architecture.md)，出题规范见 [docs/curriculum-authoring.md](docs/curriculum-authoring.md)，贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。外部课程兼容元数据被冻结在 `curriculum/external/`，不是默认路线，也不镜像上游答案或测试。

License: [Apache-2.0](LICENSE).
