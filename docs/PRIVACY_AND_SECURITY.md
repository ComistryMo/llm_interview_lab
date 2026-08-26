# 隐私与安全

## 绝对禁止进入工作树

雇主、客户、学校或其他第三方的源码、数据、配置、日志、截图、内部路径、类名、提交标识、模型名称、checkpoint、未公开指标、业务样本和文档。即使目录在 `.gitignore` 中也不应放入仓库根目录；ignore 只减少误提交，不构成隔离或授权。

## 允许的项目恢复材料

只记录重新编写的 toy implementation、公开资料、抽象流程、个人贡献边界、可公开表述和“待核实”。原始证据只能在获授权环境中由学习者本人查看，不能复制给 AI 或仓库。

使用 `templates/PROJECT_CLAIM.md`。证据类别只能写“公开文档、自有 toy 实验、本人记忆待核实”等抽象类型，不能写 locator。

## Handoff 导出

导出器是防误操作工具，不是数据防泄漏证明。它采用精确 allowlist、文本与大小限制、路径/符号链接检查、secret 模式检查和内容 hash。任何一项失败都应停止，不得改成自动递归或黑名单兜底。

安全流程：

1. 编辑 `config/export/handoff.json` 的精确文件清单；
2. 运行 `python scripts/export_handoff.py --dry-run`；
3. 人工打开每个候选文件并确认披露权；
4. 按 CLI 要求显式确认后生成；
5. 使用 `--verify` 校验归档；
6. 解压并最后人工检查再上传。

状态、review、progress 和 notes 可能含个人信息，即使已列入 allowlist，也需要 `--acknowledge-review`。

## 发现问题

尚未提交时立即移除并重新扫描。已经进入公开 Git 历史时，不要只做普通删除；停止分发，按 [SECURITY.md](../SECURITY.md) 私下报告并制定凭据轮换或历史净化方案。
