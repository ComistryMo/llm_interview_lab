# 开始使用

本页只解决冷启动：创建安全副本、验证环境、选择唯一任务和启动一次教练闭环。

## 1. 选择正确的仓库方式

公共仓库的普通 fork 适合贡献公共框架，不适合保存私人训练。GitHub 明确说明[公开 upstream 的 fork 仍是公开的，且 fork 不能单独改变可见性](https://docs.github.com/en/pull-requests/reference/forks)。当前版本尚未启用 Template Repository；请用生成器从已提交的公共 HEAD 创建独立 workspace。它会移除维护者 fixture、恢复无答案 starter、生成新的 H0/`not_started` ledger，并保留只读 `upstream` 历史。

```bash
git clone https://github.com/ComistryMo/llm_interview_lab.git llm-interview-lab-upstream
cd llm-interview-lab-upstream
python scripts/create_private_workspace.py ../my-llm-interview-lab
cd ../my-llm-interview-lab
git status --short
```

生成器拒绝已有目标、带 tracked 修改的源仓库和源仓库内部目标；不会添加 `origin`，并把 `upstream` 的 push URL 设为 `DISABLED`。此时先不要填写个人信息或推送，继续完成环境与状态验证。

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
python scripts/check_environment.py
python -m pytest -q
python scripts/validate_state.py
```

环境检查失败与训练题失败是两类问题。默认 pytest 和状态校验必须绿色；当前 Task 的定向测试可以在实现过程中为红。

全部健康检查通过后，在 GitHub 新建一个 **empty + private** repository。先审查生成器产生的 reset diff，再建立私人基线：

```bash
git add --all
git diff --cached --check
git commit -m "initialize private learner workspace"
git remote add origin <your-empty-private-repository-url>
git remote -v
git push -u origin main
```

在 GitHub 页面再次确认目标仓库是 private，才能填写个人档案。公共 starter 与 workspace 在仓库内完成物理分离后，本项目才会推荐 [GitHub Template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) 流程；模板创建的新仓库拥有独立历史并可选择可见性。

## 3. 个性化

复制 `templates/LEARNER_PROFILE.md` 的字段到你的私人 `state/LEARNER_PROFILE.md`。只写求职方向、时间预算、可公开能力基线和帮助上限。项目事实使用 `templates/PROJECT_CLAIM.md`，不要把原始证据放入仓库。

按照 [CUSTOMIZATION.md](CUSTOMIZATION.md) 选择一项当前任务，确保 `state/CURRENT_TASK.md` 与 ledger 一致。

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

## 6. 导出前检查

先编辑精确 allowlist，再运行：

```bash
python scripts/export_handoff.py --dry-run
python scripts/export_handoff.py --acknowledge-review --output dist/handoff-reviewed.zip
python scripts/export_handoff.py --verify dist/handoff-reviewed.zip
```

`--acknowledge-review` 是人工检查后的显式声明，不是交互提示。上传前仍要解压逐文件检查；扫描器不能判断一句项目描述是否受保密约束。
