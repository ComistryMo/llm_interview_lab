# External Review Handoff

> Public alpha fixture. 在私人副本中按 `templates/HANDOFF.md` 更新；导出前必须由学习者逐文件人工确认。

## 当前任务与状态

- Task：00A-1 `count_wrong_predictions`；
- 状态：`needs_revision`；
- 最高帮助：H1；
- `demonstration_only=false`。

## 测试证据

```text
python -m pytest tests/stage00/test_task_00a1.py -q
1 failed, 5 passed
```

失败原因：非整数 prediction 尚未按任务要求抛出 `ValueError`。这是当前训练反馈，不是基础设施回归。

## 已验证与待审查

- 已验证：常规计数、空输入异常、输入不变性；
- 待修订：运行时类型校验、不可达代码、循环变量命名和学员自编异常测试；
- 外部审查重点：任务文字是否完整转成代码与测试。

## 隐私人工确认

- [ ] 没有第三方源码、数据、路径、配置、日志、截图、内部标识或指标；
- [ ] 没有凭据、个人联系方式或本机绝对路径；
- [ ] 已解压并逐文件检查导出包。
