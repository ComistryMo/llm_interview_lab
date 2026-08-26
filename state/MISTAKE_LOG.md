# Mistake Log

## 2026-08-26 / Task 00A-1

### 新确认的语法

- `for i in predictions` 中 `i` 是每个元素，不是下标；
- 如果同时需要下标和元素，可以学习 `enumerate`；
- `raise ValueError("...")` 用于主动抛出输入错误。

### 错误与风险

1. `return` 后保留 `raise NotImplementedError`：该行不可达；
2. 误以为 `list[int]` 类型标注会自动校验：Python 默认不会；
3. 变量名 `i` 容易让读者误以为是 index；
4. 测试只覆盖已有用例，没有主动从任务文字推导新测试；
5. 复盘“最困难的三个点”没有写完整，说明元认知记录不足。

### 防复发规则

- 提交前搜索 `TODO`、`NotImplementedError` 和不可达代码；
- 将任务要求逐项转为 checklist；
- 每个“必须/不能为空/应为某类型”至少对应一个测试；
- 循环变量用其真实语义命名。
