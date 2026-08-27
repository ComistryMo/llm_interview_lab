# OSS LEAN-V2 MVP ExecPlan

## 目标与可观察结果

把已完成的 Vertical Slice 1 扩展为面向大众的 clone-first 训练闭环：Profile 初始化、Track 导航、固定题实现、公开测试、提交、结构化 Review、D+2/D+7 复测、mastery 与 DAG 解锁。固定课程只维护在 `curriculum/catalog/*.yaml`，个人历史只维护在 `workspace/profiles/<id>/events.jsonl`。

完成时应有至少 38 个 ready 固定题、至少 100 个仅存在于 Catalog 的 planned 节点、完整 CLI、超时和输出截断、两个 Profile 隔离测试，以及可复现的 clean-clone smoke test。

## 当前事实

- 分支：`refactor/oss-lean-v2`；起点：`e6bd6e1`。
- Python 3.11.9 虚拟环境可用；系统默认 Python 3.9.2 不作为项目 Gate。
- 基线：201 passed，4 skipped，38.03 秒；工作树干净。
- Vertical Slice 1 已有 FND-001、Catalog/DAG、内嵌 Workspace、统一 submission loader、pytest 子进程 grader 和七个 CLI 命令。
- `workspace/profiles/maintainer-v1/` 是 ignored 本地迁移副本；旧公共个人 fixture 尚未删除。

## 范围与明确不做

本计划覆盖 Grader 加固、事件生命周期、CLI、公共个人 fixture 清理、38 道 ready 题、100+ planned 节点、Track/Quest/Capstone 登记、最小 AI 教练协议、文档收敛和端到端测试。

不实现 Web、数据库、网络服务、模型 API、多 Agent Runtime、恶意代码沙箱、全局项目生成器、外部课程扩展或 Git 历史重写。`curriculum/external/` 冻结保留。

## 里程碑与测试

1. 核心生命周期：扩展 Catalog、Events、Grader、Workspace 与 CLI。
   - 定向：`python -m pytest tests/infrastructure/test_lean_v2_*.py -q`
2. 公共边界切换：再次核验 maintainer Profile 后删除 tracked 个人 fixture，调整 CI 与兼容层。
   - 定向：`llm-lab doctor`、隐私和 repository-contract tests。
3. 课程批次：Foundation；Tensor/Autograd；Loss/Optimizer；NN layer；Attention；Post-training；Agent。
   - 每批：资产契约测试、Schema/DAG、编译检查；每 4—6 题运行 Repository Health。
4. Planned Catalog 与导航：100+ planned、12 Tracks、11 Quests、8 Capstones。
   - 定向：Catalog/DAG/asset tests、`llm-lab catalog`、`llm-lab graph`。
5. 文档和教练边界：README、三份核心文档、贡献指南和四个 coach 文件。
6. 最终验收：全量测试、两个 Profile 生命周期、超时、输出截断、stale SHA、幂等、Git ignore 和 clean clone。

## 风险、回滚与停止条件

- 删除旧公共个人 fixture 前必须再次确认 ignored 副本存在、逐文件 SHA-256 一致、reducer 语义等价；任一失败即停止删除。
- 不删除 `workspace/profiles/maintainer-v1/`，不读取其内容作为公共课程素材，不重写历史。
- 每个逻辑批次单独 commit；回滚使用 `git revert <commit>`，不使用 destructive reset。
- 若课程题无法达到明确契约和至少五项独立测试，则保留为 planned，不用低质量目录凑 ready 数量。

## 决策日志

- 2026-08-27：保留 repository-local、clone-first 产品形态；PyTorch 为可选依赖，第一题不要求安装 PyTorch。
- 2026-08-27：Review 使用确定性的结构化人工/AI 教练输入；mastery 只由 reducer 可验证证据推导。
- 2026-08-27：Retention 使用新的空 attempt 和 Catalog 中的固定变式契约；不复制或展示旧答案。
- 2026-08-27：课程测试继续通过唯一 pytest plugin 注入 Workspace submission；根 pytest 永不收集课程测试。
- 2026-08-27：执行本地受信任代码；路径约束、超时和截断不宣称为安全沙箱。

## 当前进度

- [x] Python 3.11 基线与完整测试确认。
- [ ] 核心生命周期与 CLI。
- [ ] 公共个人 fixture 安全清理。
- [ ] 38 道 ready 题。
- [ ] 100+ planned 节点和导航对象。
- [ ] 文档与 Coach 边界收敛。
- [ ] 最终全量与 clean-clone 验收。

## 最终复盘

完成后填写实际资产数、节点数、测试证据、迁移结果、提交列表、限制和下一版本建议，并将本文件移动到 `plans/completed/`。
