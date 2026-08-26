# 外部参考与来源治理

本项目可以学习其他开源项目的抽象组织机制，但默认不复制其正文、代码、测试、公式、图示、Notebook 或基准数字。`references/registry.json` 记录实际影响过仓库设计的来源，不是“推荐阅读大全”。

## 何时必须登记

出现以下任一情况时，在合并前登记来源：

- 外部仓库影响了任务结构、导航、测试策略或工具设计；
- 课程要求学习者在 Preview 或 review 后查看特定外部材料；
- 实现或文档准备改编、翻译或移植第三方内容；
- benchmark 的工作负载、口径或基线来自外部项目。

仅仅使用 Python、PyTorch 等通用 API 不需要逐项登记，但任务卡仍应优先链接官方文档。

## 登记要求

- repository 必须固定完整 40 位 commit SHA；
- `audited_on` 是人工审计日期，不表示持续同步；
- 许可证按材料范围分别记录，链接到固定 revision 的证据，并说明可复核的 `license_audit_method`；
- `influence` 只写本仓库独立采用的抽象机制；
- `excluded_material` 明确哪些内容没有复制；
- Task 引用必须声明 `preview-safe` 或 `post-review-only`；
- 网络不可用时本地训练和 CI 仍应工作。

登记记录同时包含 `license_status`。只有在固定 revision 找到并登记了许可证证据，状态才可为 `verified`；未发现许可证时使用 `not-found`、保持许可证列表为空，并按“没有再分发许可”处理，而不是猜测上游意图。

许可证登记不是法律结论。若要实际复制或改编第三方材料，必须另开小范围 PR，核实作者、许可证、NOTICE/署名要求和兼容性；无法证明来源或授权时停止合并。

## 当前参考的边界

`datawhalechina/llm-algo-leetcode` 只作为设计级参考。我们独立实现“双轴发现、runtime 声明、统一校验和实验证据边界”这些机制；不采用其 Notebook 内嵌答案模式。本仓库的差异化目标是证明学习者在受控 AI 帮助下能够独立实现、解释、调试并通过 D+2/D+7 迁移，而不是再做一套大模型算法教程镜像。

Stanford CS336 Spring 2026 课程页所链接的 Assignment 1–5 作为 `external-course-source` 登记。它们只通过固定 commit 的外部 checkout 使用；仓库内保存独立编写的 inventory、资源分类和教练 Gate。A1–A4 的审计版本有 MIT 证据；对 A5 固定 tree 的递归文件名审计未发现许可证文件，因此不推定再分发许可。A5 仅转录兼容与审计所需的事实性名称、路径、命令和计数，不复制或翻译正文、实现、测试体、prompt、fixture、数据或答案。详情见[外部课程包政策](EXTERNAL_COURSE_PACKS.md)。

## Review 清单

1. registry 是否固定到完整 commit，而不是 `main`？
2. 许可证证据是否也固定到同一 commit？
3. Task 的暴露级别是否会破坏闭卷实现？
4. 新增内容能否由贡献者说明为独立创作？
5. 是否误带公司、客户、个人或未公开材料？
6. benchmark 是否区分 synthetic、公开数据和真实项目事实？
