# 开始使用

本页只解决冷启动：创建安全副本、验证环境、选择唯一任务和启动一次教练闭环。

## 1. 选择正确的仓库方式

公共仓库的普通 fork 适合贡献公共框架，不适合保存私人训练。GitHub 明确说明[公开 upstream 的 fork 仍是公开的，且 fork 不能单独改变可见性](https://docs.github.com/en/pull-requests/reference/forks)。当前版本尚未启用 Template Repository；请用生成器从已提交的公共 HEAD 创建独立 workspace。它会移除维护者 fixture、恢复无答案 starter、生成新的 H0/`not_started` ledger，随后丢弃公共提交历史并建立全新的 `main` 分支。公共仓库只作为禁止 push 的 `upstream` 地址保留。

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git llm-interview-lab-upstream
cd llm-interview-lab-upstream
python scripts/create_private_workspace.py ../my-llm-interview-lab
cd ../my-llm-interview-lab
git status --short
```

生成器拒绝已有目标、带 tracked 修改的源仓库和源仓库内部目标；不会添加 `origin`，并把 `upstream` 的 push URL 设为 `DISABLED`。生成结果没有 commit，所有基线文件已暂存供审查。此时先不要填写个人信息或推送，继续完成环境与状态验证。

## 2. 创建环境

```bash
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

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
git diff --cached --check
python scripts/check_environment.py
python -m pytest -q
python scripts/validate_state.py
```

环境检查失败与训练题失败是两类问题。默认 pytest 和状态校验必须绿色；当前 Task 的定向测试可以在实现过程中为红。

全部健康检查通过后，在 GitHub 新建一个 **empty + private** repository。逐文件审查已暂存的全新基线，再提交并推送：

```bash
git diff --cached --check
git commit -m "initialize private learner workspace"
git remote add origin <your-empty-private-repository-url>
git remote -v
git push -u origin main
```

在 GitHub 页面再次确认目标仓库是 private，才能填写个人档案。公共 starter 与 workspace 在仓库内完成物理分离后，本项目才会推荐 [GitHub Template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) 流程；模板创建的新仓库拥有独立历史并可选择可见性。

## 3. 个性化

复制 `templates/LEARNER_PROFILE.md` 的字段到你的私人 `state/LEARNER_PROFILE.md`。只写求职方向、时间预算、可公开能力基线和帮助上限。项目事实使用 `templates/PROJECT_CLAIM.md`，不要把原始证据放入仓库。

新生成的私人 workspace 已把 `00A-1` 注册为唯一当前任务。首次使用不要手改 ledger 或跳题；先按 [CUSTOMIZATION.md](CUSTOMIZATION.md) 调整非敏感档案，并完成当前 Gate。可以用只读预览确认路由：

```bash
python scripts/select_current_task.py 00A-1
```

当前任务至少 `reviewed` 后，再预览下一项；确认机器前置、Task Card 中的人类/资源 Gate 与唯一任务边界后才应用：

```bash
python scripts/select_current_task.py <TASK-ID>
python scripts/select_current_task.py <TASK-ID> --apply --acknowledge-human-gates
```

选择器默认 dry-run；`--apply` 只在需要时追加 `task_registered` 事件并重建 `state/CURRENT_TASK.md`，不执行答案或测试。若确需暂停一个尚未 `reviewed` 的任务，必须额外写出原因并显式使用 `--acknowledge-paused-current`；它不会把旧任务判为通过。当前外部 pack 的状态是 `inventory-audited`，原生 readiness 尚未形成机器映射，因此外部 canonical ID 只能 Preview，不能用布尔声明绕过 Gate；后续任务包把它升级为 `implementation-ready` 后才允许应用。

用结构化元数据动态检查或运行当前原生任务，避免复制过期测试命令：

```bash
python scripts/run_current_task.py --dry-run
python scripts/run_current_task.py
```

若当前任务是外部课程 problem group，脚本会拒绝自动执行第三方代码并指向人工审阅入口。

## 4. 启动 AI 教练

将下面文本交给能够读取仓库的 AI：

```text
读取 AGENTS.md、state/LEARNER_PROFILE.md、state/CURRENT_TASK.md、
docs/COACHING_PROTOCOL.md 和当前任务卡。运行定向测试但不要修改 src。
用不超过 10 条复述状态，然后只告诉我唯一下一步。
```

助手不能运行终端时，要求它明确标记“测试未运行”，由你粘贴精简输出。能力差异见 [AI_COACH_ADAPTER.md](AI_COACH_ADAPTER.md)。

## 5. 完成一次闭环

实现后发送“提交当前 Task，只审查不要改答案”。教练应给证据、最多三个问题和一个下一步。首次全绿不是 mastery；按照状态模型完成口述、D+2 和 D+7。

## 6. 可选外部课程包

当前外部 pack 处于 `inventory-audited`，只允许安装、检查和 Preview；原生 readiness 尚未形成可校验映射，因此现在不能把外部任务应用到 Implementation Lane。你仍可先完成对应原生前置 Gate，再从[外部课程导航](../curriculum/external/NAVIGATION.md)预览一个 canonical problem-group Task。外部 pack 不会自动替你更改当前任务；安装只准备固定 checkout。

```bash
python scripts/manage_external_course.py list
python scripts/manage_external_course.py show EXT-CS336-A1
python scripts/manage_external_course.py show-group EXT-CS336-A1-tokenizer-core
python scripts/select_current_task.py EXT-CS336-A1-tokenizer-core
```

最后一条是只读预览，并会明确报告尚未机器解锁的 readiness。未来 pack 升级为 `implementation-ready` 后，正式实施仍须把该 group 登记为私人 ledger 中唯一的 `CURRENT_TASK`，同时暂停原生 Implementation Lane。安装前必须阅读[许可证、学术诚信和资源边界](EXTERNAL_COURSE_PACKS.md)。官方 assignment 的 AI 上限与原生任务不同，不得用“允许直接实现”绕过官方政策。

## 7. 导出前检查

先编辑精确 allowlist，再运行：

```bash
python scripts/export_handoff.py --dry-run
python scripts/export_handoff.py --acknowledge-review --output dist/handoff-reviewed.zip
python scripts/export_handoff.py --verify dist/handoff-reviewed.zip
```

`--acknowledge-review` 是人工检查后的显式声明，不是交互提示。上传前仍要解压逐文件检查；扫描器不能判断一句项目描述是否受保密约束。
