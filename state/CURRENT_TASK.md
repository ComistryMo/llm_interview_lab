# Current Task

<!-- CURRENT_TASK_STATE
{"assistance_level":"H1","attempt_id":"00A-1-A001","demonstration_only":false,"latest_event_id":"evt-00A-1-legacy-001","requires_independent_variant":false,"schema_version":1,"status":"needs_revision","task_id":"00A-1"}
END_CURRENT_TASK_STATE -->

## 基本信息

- Task：00A-1 `count_wrong_predictions`
- 状态：`needs_revision`
- 帮助等级：H1（询问了 `ValueError` 语法和 `for ... in ...` 的迭代语义）
- 完整定向测试：5 passed, 1 failed（非 int 输入未抛出 ValueError）

## 当前实现事实

核心循环逻辑正确：逐个遍历元素，与 label 比较并计数。

## 已满足

- 空列表抛出 `ValueError`；
- 正确统计常规输入；
- 不修改输入；
- 时间复杂度 `O(n)`；
- 额外空间 `O(1)`。

## 尚未满足

1. 任务要求“每个预测都应是 int”，当前没有运行时校验；
2. `return nums` 后仍保留 `raise NotImplementedError`，属于不可达死代码；
3. 变量名 `i` 实际表示元素，不是下标，建议改为 `prediction`；
4. 学习者没有自己增加类型异常测试；
5. “最困难的三个点”复盘不完整。

## 本次唯一任务

修订 Task 00A-1，不进入 00A-2：

- 删除不可达代码；
- 改善变量名；
- 校验每个 prediction 的类型并抛出 `ValueError`；
- 添加至少一个非 int 的失败测试；
- 运行定向测试；
- 用自己的话回答任务六个验收问题。

## 定向测试

```bash
python -m pytest tests/stage00/test_task_00a1.py -q
```

## AI 教练行为

- 默认只审查和提示，不直接修改 `src/stage00/hard_sample_miner.py`；
- 一级提示可以解释“类型标注不做运行时检查”；
- 不给完整函数；
- 通过正式 review 后记录带时区时间戳，并据此计算最早闭卷时间。

## 复测计划

- D+2：`review_passed` 后至少 48 小时，H0 闭卷重写，日期待定；
- D+7：`review_passed` 后至少 7 天，H0 结构变式，日期待定；
- D+21：`review_passed` 后至少 21 天，综合困难样本题，日期待定。
