# 课程元数据契约

`curriculum/catalog.json` 是公共课程的机器可读索引，`curriculum/NAVIGATION.md` 是它的确定性派生视图。Task Card 仍是任务要求的权威来源；catalog 只承载发现、依赖、运行和公开成熟度信息。

## 三种不能混淆的状态

| 概念 | 权威来源 | 回答的问题 |
|---|---|---|
| 公共成熟度 `public_maturity` | `curriculum/catalog.json` | 这套公开任务材料是否可供稳定训练？ |
| 学习者状态 | `state/TASK_LEDGER.jsonl` | 某个学习者做到了哪一步？ |
| 当前任务 | `state/CURRENT_TASK.md` | Implementation Lane 此刻只做哪一项？ |

`validated` 绝不表示学习者已实现或掌握；`mastered` 也不能反向证明公共任务包质量已经过多人验证。

## 字段边界

每个 task 记录：

- 唯一 ID、stage、稳定顺序和 Task Card 路径；
- 结构化前置任务及最低学习者状态；
- 非任务型 Gate 要求；
- P0/P1/P2、难度和独立实现时间区间；
- 学习目标与面试价值；
- `draft`、`review-ready` 或 `validated` 公共成熟度；
- 最低 runtime、GPU 验收策略和精确 pytest node；
- 岗位路线、数学前置和外部参考暴露策略；
- 是否只是未来公开作品候选。候选不等于可迁出。

受控枚举：

- `runtime_profile`：`python-cpu`、`pytorch-cpu`、`pytorch-cuda`；
- `gpu_acceptance_policy`：`not-applicable`、`cpu-required-gpu-optional`、`cuda-required`；
- `reference_exposure`：`none`、`preview-safe`、`post-review-only`；
- `difficulty`：`introductory`、`intermediate`、`advanced`。

外部教程含答案时必须用 `post-review-only`，不得放进当前任务的 Preview Lane。`preview-safe` 只允许不泄露实现的官方接口、公式或背景资料。

## 单一事实源策略

- Task Card 保存输入输出、边界、提示、口述和复测契约；
- catalog 保存跨任务检索和机器校验所需的最小摘要；
- 导航页不得手工维护；修改 catalog 后运行生成命令；
- 长期路线可以描述尚不存在的能力，但 catalog 不能登记没有完整 Task Card 的空任务。

## 维护命令

```bash
python scripts/validate_curriculum.py --write-navigation
python scripts/validate_curriculum.py
python -m pytest tests/infrastructure/test_validate_curriculum.py -q
```

校验器离线工作，检查严格字段、UTF-8、重复 JSON key、精确大小写路径、测试节点、依赖 DAG、stage 顺序、runtime/GPU 组合、参考引用和生成页漂移。它不会联网判断上游仓库是否更新；升级参考版本必须人工重新审计并提交 registry diff。
