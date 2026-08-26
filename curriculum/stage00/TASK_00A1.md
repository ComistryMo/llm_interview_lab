# Task 00A-1：统计错误预测次数

## 背景

使用完全虚构的 toy 数据，模拟“同一样本推理多次，统计错误次数”的流程。不得使用任何公司内部数据。

## 目标函数

```python
def count_wrong_predictions(label: int, predictions: list[int]) -> int:
    ...
```

## 要求

- `predictions` 不能为空；
- 每个预测必须是 `int`；
- 返回与 `label` 不相等的元素数量；
- 不修改输入列表；
- 正确异常使用 `ValueError`；
- 使用清楚的变量名；
- 无不可达代码。

## 学习点

- `for value in collection` 中变量是元素，而不是下标；
- 如需下标可使用 `enumerate`；
- 类型标注不会在运行时自动校验；
- `return` 后的同层语句不可达；
- 循环计数的时间复杂度和空间复杂度。

## 定向测试

```bash
python -m pytest tests/stage00/test_task_00a1.py -q
```

## 验收问答

1. `for i in predictions` 中 `i` 是什么？
2. 怎样同时获得下标和元素？
3. 为什么 `list[int]` 不会自动拒绝字符串？
4. 该实现的时间和空间复杂度是什么？
5. 为什么不会修改原列表？
6. `return` 后再写 `raise` 会怎样？

## 间隔复测

- D+2：不看旧代码重写同函数；
- D+7：输入改为 `list[bool]`/多类别或要求返回错误位置，按新题说明处理；
- D+21：作为困难样本筛选综合题的一部分重写。
