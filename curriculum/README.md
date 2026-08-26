# Curriculum

`curriculum/` 保存任务契约、公共索引和依赖，不保存完整答案。

- `stage00/`：真实小任务中的 Python/PyTorch 基础；
- `catalog.json`：机器可读的任务发现、依赖、runtime、测试和参考暴露元数据；
- `NAVIGATION.md`：由 catalog 确定性生成的依赖轴 × 岗位轴导航；
- `CORE_40.md`：长期核心手撕索引，不等于全部已实现；
- 当前唯一任务以 `state/CURRENT_TASK.md` 为准。

新增 Task 必须有唯一 ID、前置 Gate、输入输出、第一版范围、明确不做、边界、可见测试、分级提示、口述问题、D+2/D+7 变式和降级任务。课程文件的存在不代表任务已解锁。

Task Card 是任务契约的权威来源，catalog 是跨任务索引的权威来源，学习者状态只来自私人 ledger。不要手工编辑生成导航，也不要用 `public_maturity` 推断个人掌握状态。字段与维护流程见[课程元数据契约](../docs/CURRICULUM_METADATA.md)。

```bash
python scripts/validate_curriculum.py --write-navigation
python scripts/validate_curriculum.py
```
